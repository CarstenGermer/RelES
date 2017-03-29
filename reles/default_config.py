from __future__ import absolute_import, unicode_literals

from decouple import Config, Csv, RepositoryIni
from pathlib2 import Path

from .auth.models import Customer, User, auth_index

# TODO should we pull the path from cli args or an env var?
config_path = str(Path(Path(__file__).parent, '../configs/settings.ini').resolve())
config = Config(RepositoryIni(config_path))

BASE_DIR = str(Path(__file__).parent)
ROOT_DIR = str(Path(__file__).parent.parent)

PORT = config('PORT', default=8080, cast=int)

DEBUG = config('DEBUG', default=False, cast=bool)
TESTING = config('TESTING', default=False, cast=bool)

SECRET_KEY = config('SECRET_KEY')

AUTH_JWT_ALGORITHM = config('AUTH_JWT_ALGORITHM', default='HS512')
AUTH_JWT_SECRET = config('AUTH_JWT_SECRET', default='phukoo9EMie5mei1yaeteeN')
AUTH_TOKEN_ISSUER = config('AUTH_TOKEN_ISSUER', default='RelES')
AUTH_TOKEN_LIFETIME = config('AUTH_TOKEN_LIFETIME', default=36000, cast=int)

CYCLES_CRUD = config('CYCLES_CRUD', default=1)
CYCLES_FACTOR_REFRESH = config('CYCLES_FACTOR_REFRESH', default=2)
CYCLES_GET_ARCHIVED_DOCUMENT = config('CYCLES_GET_ARCHIVED_DOCUMENT', default=1)
CYCLES_FILE_UPLOAD = config('CYCLES_FILE_UPLOAD', default=1)
CYCLES_GEOCODING = config('CYCLES_GEOCODING', default=1)

ELASTICSEARCH_HOST = config('ELASTICSEARCH_HOST')
ELASTICSEARCH_MAPPINGS = config(
    'ELASTICSEARCH_MAPPINGS',
    default={
        auth_index: [
           Customer,
           User
        ]
    },
)
ELASTICSEARCH_NON_RESETTABLE_INDEX_SETTINGS = config(
    'ELASTICSEARCH_NON_RESETTABLE_INDEX_SETTINGS',
    default=[
        'number_of_shards',
    ]
)

SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')
SQLALCHEMY_ECHO = config('SQLALCHEMY_ECHO', default=False, cast=bool)
SQLALCHEMY_TRACK_MODIFICATIONS = config('SQLALCHEMY_TRACK_MODIFICATIONS', default=False, cast=bool)

UPLOAD_HOST = config('UPLOAD_HOST')
UPLOAD_MNT = config('UPLOAD_MNT')
