import os
from pathlib import Path


BASE_PATH = Path(os.getenv('DIRECTORY_PATH', './data')).resolve()
SQL_DATABASE_PATH = os.getenv("SQL_DATABASE_PATH", "./database/app.db")
SQLALCHEMY_DATABASE_URL = f'sqlite:///{SQL_DATABASE_PATH}'
PORT = int(os.getenv('PORT', '8000'))
HOST = os.getenv('HOST', '0.0.0.0')
RUN_MIGRATIONS = os.getenv('RUN_MIGRATIONS', 'false') == 'true'
ALEMBIC_INI_PATH = os.getenv('ALEMBIC_INI_PATH', './alembic.ini')
