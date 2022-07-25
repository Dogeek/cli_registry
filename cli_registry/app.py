from base64 import b85decode
from datetime import datetime
from http import HTTPStatus
import logging
from logging.config import dictConfig
import os
from textwrap import shorten
from typing import Optional

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from cli_registry.config import BASE_PATH
from cli_registry.models.maintainer import MaintainerOrm, MaintainerModel
from cli_registry.models.plugin import (
    PluginOrm, PluginVersionOrm, PluginModel, PluginVersionModel,
)
from cli_registry import dependancies as deps


log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",

        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "foo-logger": {"handlers": ["default"], "level": "DEBUG"},
    },
}
dictConfig(log_config)

app = FastAPI()
logger = logging.getLogger('cli_registry')


@app.get('/v1/plugins')
async def list_plugins(page: int = 1, page_size: int = 10, db: Session = Depends(deps.db)):
    '''Lists available plugins on this registry.'''
    plugins: list[PluginOrm] = (
        db
        .query(PluginOrm)
        .limit(page_size)
        .offset(page_size * (page - 1))
        .all()
    )
    return {
        'status': 'ok',
        'data': [plugin.dict() for plugin in plugins],
    }


@app.get('/v1/plugins/{plugin_name}')
async def get_plugin(plugin: PluginOrm = Depends(deps.plugin)):
    '''Get a specific plugin definition by name.'''
    return {
        'status': 'ok',
        'data': plugin.dict(),
    }


@app.get('/v1/plugins/{plugin_name}/versions')
async def list_plugin_versions(plugin: PluginOrm = Depends(deps.plugin)):
    '''List available versions of a given plugin.'''
    return {
        'status': 'ok',
        'data': [version.dict(with_file=False) for version in plugin.versions]
    }


@app.get('/v1/plugins/{plugin_name}/versions/latest')
async def get_plugin_version_latest(plugin: PluginOrm = Depends(deps.plugin)):
    '''Gets the latest version of a given plugin.'''
    return {
        'status': 'ok',
        'data': plugin.latest_version.dict()
    }


@app.get('/v1/plugins/{plugin_name}/versions/{version}')
async def get_plugin_version(plugin_version: PluginVersionOrm = Depends(deps.plugin_version)):
    '''Gets a specific version of a given plugin.'''
    return {
        'status': 'ok',
        'data': plugin_version.dict()
    }


@app.post('/v1/plugins')
async def create_plugin(
    plugin_data: PluginModel, db: Session = Depends(deps.db),
    x_maintainer_email: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
):
    '''Creates a new plugin definition.'''
    if authorization is None:
        raise HTTPException(
            HTTPStatus.FORBIDDEN,
            'Authorization header not provided.'
        )

    existing_plugin = (
        db
        .query(PluginOrm)
        .filter(PluginOrm.name == plugin_data.name)
        .first()
    )
    if existing_plugin is not None:
        raise HTTPException(
            HTTPStatus.NOT_ACCEPTABLE,
            'A plugin with this name already exists.'
        )

    maintainer: Optional[MaintainerOrm] = (
        db
        .query(MaintainerOrm)
        .filter(MaintainerOrm.ssh_key == authorization)
        .first()
    )
    if maintainer is None:
        # Create maintainer
        maintainer = MaintainerOrm()
        maintainer.ssh_key = authorization
        maintainer.email = x_maintainer_email
        db.add(maintainer)
    plugin_orm = PluginOrm()
    plugin_orm.name = plugin_data.name
    plugin_orm.maintainers.append(maintainer)
    db.add(plugin_orm)
    db.commit()
    return JSONResponse({'status': 'ok'}, HTTPStatus.CREATED)


@app.get('/v1/plugins/{plugin_name}/maintainers')
async def list_plugin_maintainers(
    plugin: PluginOrm = Depends(deps.plugin),
):
    '''Lists available maintainers for a plugin.'''
    return {'status': 'ok', 'data': [m.dict() for m in plugin.maintainers]}


@app.post('/v1/plugins/{plugin_name}/maintainers', dependencies=[Depends(deps.authentication)])
async def add_maintainer_to_plugin(
    maintainer: MaintainerModel,
    db: Session = Depends(deps.db),
    plugin: PluginOrm = Depends(deps.plugin),
):
    '''Add a maintainer to the plugin.'''
    # Try to find maintainer if it exists
    maintainer_orm = (
        db
        .query(MaintainerOrm)
        .filter(MaintainerOrm.ssh_key == maintainer.ssh_key)
        .first()
    )
    status = HTTPStatus.OK
    if maintainer_orm is None:
        maintainer_orm = MaintainerOrm()
        maintainer_orm.ssh_key = maintainer.ssh_key
        maintainer_orm.email = maintainer.email
        status = HTTPStatus.CREATED
        db.add(maintainer_orm)
    plugin.maintainers.append(maintainer_orm)
    db.commit()
    return JSONResponse({'status': 'ok'}, status)


@app.post(
    '/v1/plugins/{plugin_name}/versions/{version}',
    dependencies=[Depends(deps.authentication)]
)
async def create_plugin_version(
    version: str, data: PluginVersionModel,
    db: Session = Depends(deps.db),
    plugin: PluginOrm = Depends(deps.plugin),
):
    '''Publish a new version of the plugin to the registry.'''
    print(
        'Creating a new plugin version for plugin %s (%s)' % (plugin.name, version)
    )
    version_orm = PluginVersionOrm()
    version_orm.version = version
    version_orm.plugin = plugin
    version_orm.upload_date = datetime.now()
    db.add(version_orm)
    db.commit()
    print('Plugin version created and committed successfully.')

    plugin_path = BASE_PATH / f'{plugin.name}/'
    print('Saving version to path %s' % plugin_path)
    plugin_path.mkdir(parents=True, exist_ok=True)
    print('Making the directory if it does not exist...')
    with open(plugin_path / f'{version}.tar.gz', 'wb') as fp:
        print(
            'Opened file pointer to %s and writing...' % str(plugin_path / f'{version}.tar.gz')
        )
        print('Raw data : %s' % shorten(data.tarball, 50))
        fp.write(b85decode(data.tarball))
    return JSONResponse({'status': 'ok'}, HTTPStatus.CREATED)


@app.delete('/v1/plugins/{plugin_name}', dependencies=[Depends(deps.authentication)])
async def delete_plugin(
    db: Session = Depends(deps.db),
    plugin: PluginOrm = Depends(deps.plugin),
):
    '''Delete a plugin and all its versions from the registry.'''
    for version in plugin.versions:
        os.remove(version.file_path)
    db.delete(plugin)
    db.commit()
    return JSONResponse({'status': 'ok'}, HTTPStatus.NO_CONTENT)


@app.delete(
    '/v1/plugins/{plugin_name}/versions/{version}',
    dependencies=[Depends(deps.authentication)]
)
async def delete_plugin_version(
    plugin_version: PluginVersionOrm = Depends(deps.plugin_version),
    db: Session = Depends(deps.db),
):
    '''Delete a plugin's version from the registry'''
    os.remove(plugin_version.file_path)
    db.delete(plugin_version)
    db.commit()
    return JSONResponse({'status': 'ok'}, HTTPStatus.NO_CONTENT)
