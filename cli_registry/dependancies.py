from http import HTTPStatus

from fastapi import Depends, Path, HTTPException, Request, Header
from sqlalchemy.orm import Session

from cli_registry.db import SessionLocal
from cli_registry.models.plugin import PluginOrm, PluginVersionOrm
from cli_registry.utils import check_auth


def db() -> Session:
    the_db = SessionLocal()
    try:
        yield the_db
    finally:
        the_db.close()


def plugin(
    plugin_name: str = Path(),
    db: Session = Depends(db)
) -> PluginOrm:
    plugin: PluginOrm | None = (
        db
        .query(PluginOrm)
        .filter(PluginOrm.name == plugin_name)
        .first()
    )
    if plugin is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f'Plugin {plugin_name} not found.'
        )
    return plugin


def plugin_version(
    version: str = Path(),
    db: Session = Depends(db),
    plugin: PluginOrm = Depends(plugin),
):
    version_db: PluginVersionOrm | None = (
        db
        .query(PluginVersionOrm)
        .filter(PluginVersionOrm.plugin_id == plugin.id, PluginVersionOrm.version == version)
        .first()
    )
    if version_db is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f'Version {version} not found for plugin {plugin.name}.'
        )
    return version_db


def authentication(
    request: Request,
    plugin: PluginOrm = Depends(plugin),
    authorization: str | None = Header(default=None),
    x_signature: str | None = Header(default=None),
):
    if authorization is None:
        raise HTTPException(
            HTTPStatus.FORBIDDEN,
            'Authorization header not set.'
        )
    if x_signature is None:
        raise HTTPException(
            HTTPStatus.FORBIDDEN,
            'X-Signature header not set.'
        )
    maintainers = [m.ssh_key for m in plugin.maintainers]
    if authorization not in maintainers:
        raise HTTPException(
            HTTPStatus.FORBIDDEN,
            'Key not in maintainers whitelist.'
        )
    message = request.url.path.encode('utf8')
    print(request.url.path)
    if not check_auth(message, authorization, x_signature):
        raise HTTPException(
            HTTPStatus.FORBIDDEN,
            f'Signature {x_signature} is not valid for public key {authorization}',
        )
