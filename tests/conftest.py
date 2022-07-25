from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.engine import Connection

from cli_registry.app import app
from cli_registry.db import Base
from cli_registry import dependancies as deps
from cli_registry.models.plugin import PluginOrm, PluginVersionOrm
from cli_registry.models.maintainer import MaintainerOrm


@pytest.fixture(scope="session")
def connection() -> Connection:
    engine = create_engine(
        'sqlite:///./tests/data/database.db?check_same_thread=False'
    )
    return engine.connect()


def seed_database(session: Session, data_dir: Path):
    plugins = [
        {
            "id": 1,
            "name": "plugin_1",
        },
        {
            "id": 2,
            "name": "plugin_2",
        },
        {
            "id": 3,
            "name": "plugin_3",
        }
    ]

    versions = [
        {
            "id": 1,
            "upload_date": datetime(2022, 1, 1, 0, 0, 0),
            "version": "1.0.0",
            "plugin_id": 1
        },
        {
            "id": 2,
            "upload_date": datetime(2022, 1, 2, 0, 0, 0),
            "version": "1.1.0",
            "plugin_id": 1
        },
        {
            "id": 3,
            "upload_date": datetime(2022, 1, 3, 0, 0, 0),
            "version": "2.0.0",
            "plugin_id": 1
        },
        {
            "id": 4,
            "upload_date": datetime(2022, 1, 4, 0, 0, 0),
            "version": "1.0.0",
            "plugin_id": 2
        },
        {
            "id": 5,
            "upload_date": datetime(2022, 1, 5, 0, 0, 0),
            "version": "2.0.1",
            "plugin_id": 1
        },
        {
            "id": 6,
            "upload_date": datetime(2022, 1, 1, 0, 0, 0),
            "version": "1.0.0",
            "plugin_id": 3
        }
    ]

    maintainers = [
        {
            "id": 1,
            "email": "john.doe@example.com",
        },
        {
            "id": 2,
            "email": "spam.eggs@example.com",
        },
        {
            "id": 3,
            "email": "foo.bar@example.com",
        }
    ]
    for i, maintainer in enumerate(maintainers):
        name = maintainer['email'].split('@')[0]
        maintainers[i]['ssh_key'] = (data_dir / f'maintainers/{name}.pub').read_text()

    # plugin_id : maintainer_ids
    plugin_maintainer_association = {
        1: [1, 2],
        2: [2],
        3: [1, 3],
    }

    db_maintainers = []

    for maintainer in maintainers:
        db_maintainer = MaintainerOrm(**maintainer)
        session.add(db_maintainer)
        db_maintainers.append(db_maintainer)
    for plugin_id, plugin in enumerate(plugins, start=1):
        db_plugin = PluginOrm(**plugin)
        for maintainer_id in plugin_maintainer_association[plugin_id]:
            db_plugin.maintainers.append(db_maintainers[maintainer_id - 1])
        session.add(db_plugin)
    for version in versions:
        db_version = PluginVersionOrm(**version)
        session.add(db_version)

    session.commit()


@pytest.fixture(scope="session")
def setup_database(connection: Connection):
    Base.metadata.bind = connection
    Base.metadata.create_all()

    yield

    Base.metadata.drop_all()


@pytest.fixture
def db_session(setup_database, connection: Connection, data_dir: Path):
    transaction = connection.begin()
    session = scoped_session(
        sessionmaker(autocommit=False, autoflush=False, bind=connection)
    )
    seed_database(session, data_dir)
    yield session
    transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        return db_session
    app.dependency_overrides[deps.db] = override_get_db
    test_client = TestClient(app)
    yield test_client

    db_session.close()


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent / 'data'


@pytest.fixture
def pub_key_johndoe(data_dir: Path) -> str:
    return (data_dir / 'maintainers/john.doe.pub').read_text()


@pytest.fixture
def priv_key_johndoe(data_dir: Path) -> str:
    return (data_dir / 'maintainers/john.doe').read_text()


@pytest.fixture
def pub_key_newguy(data_dir: Path) -> str:
    return (data_dir / 'maintainers/new.guy.pub').read_text()


@pytest.fixture
def priv_key_newguy(data_dir: Path) -> str:
    return (data_dir / 'maintainers/new.guy').read_text()


@pytest.fixture
def pub_key_foobar(data_dir: Path) -> str:
    return (data_dir / 'maintainers/foo.bar.pub').read_text()


@pytest.fixture
def priv_key_foobar(data_dir: Path) -> str:
    return (data_dir / 'maintainers/foo.bar').read_text()


@pytest.fixture
def pub_key_spameggs(data_dir: Path) -> str:
    return (data_dir / 'maintainers/spam.eggs.pub').read_text()


@pytest.fixture
def priv_key_spameggs(data_dir: Path) -> str:
    return (data_dir / 'maintainers/spam.eggs').read_text()


@pytest.fixture
def file(data_dir: Path) -> dict:
    data = (data_dir / 'plugin.tar.gz').read_bytes()
    return {
        'file': (
            '3.0.0.tar.gz', data, 'application/tar+gzip'
        )
    }
