'''
Registry for the CLI app
'''
__version__ = '1.0.0'

from alembic.config import Config
from alembic import command
import uvicorn

from cli_registry.app import app
from cli_registry.config import HOST, PORT, RUN_MIGRATIONS, ALEMBIC_INI_PATH


def main():
    if RUN_MIGRATIONS:
        alembic_cfg = Config(ALEMBIC_INI_PATH)
        command.upgrade(alembic_cfg, "head")
    else:
        uvicorn.run(app, host=HOST, port=PORT)
