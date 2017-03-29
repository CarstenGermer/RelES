from __future__ import absolute_import, print_function

from collections import OrderedDict
from functools import partial
import httplib
import logging
import os

from dotenv import find_dotenv, load_dotenv
from elasticsearch.client import ClusterClient
from flask import Flask
from geopy import GoogleV3
from pathlib2 import Path
import json
from jsonschema import RefResolver
from swagger_spec_validator.validator20 import validate_spec

from . import views
from .auth.middleware import authenticate_user
from .auth.models import auth_index, Customer, User
from .auth.utils import create_oauth_flow
from .persistence import SwaggerSchemaStore, DataStore, configure_elasticsearch
from .auth.views import auth
from . import swagger

# if there is a .env file, pull it in as early as possible. by setting raise_error_if_not_found
# and catching the exception, we stop it from polluting our logs
try:
    load_dotenv(find_dotenv(raise_error_if_not_found=True))
except IOError:
    # expected if user has no .env
    pass


_pattern_collection = '/<index>/<doc_type>/'
_pattern_document = '/<index>/<doc_type>/<id>'
_pattern_search = _pattern_collection + '_search'
_pattern_retrieve_archive = _pattern_document + '/_archive'

_path_map = {
    # CRUD + L
    'create': (_pattern_collection, views.create_document, ['post']),
    'retrieve': (_pattern_document, views.retrieve_document, ['get']),
    'update': (_pattern_document, views.update_document, ['put']),
    'delete': (_pattern_document, views.delete_document, ['delete']),
    'list': (_pattern_collection, views.list_documents, ['get']),

    # our special endpoints
    'search': (_pattern_search, views.search_documents, ['post']),
    'retrieve_archived': (
        _pattern_retrieve_archive, views.retrieve_archived_document, ['get']
    )
}


def configure_app(app):
    # type: (flask.app.Flask) -> None

    from . import default_config
    app.config.from_object(default_config)


def configure_endpoints(app):
    # FIXME we add the cdn prefix so the rule for `document_retrieve` does not handle downloads...
    app.add_url_rule(
        '/cdn/files/',
        'upload_file',
        views.upload_file,
        methods=['POST'],
        defaults={'index': 'media'},
    )
    app.add_url_rule(
        '/cdn/files/<path:filename>',
        'download_file',
        views.download_file,
        methods=['GET'],
        defaults={'index': 'media'},
    )

    app.add_url_rule(
        '/swagger/',
        'swagger_root',
        views.get_swagger_spec,
        methods=['GET'],
        defaults={'endpoint_': None}
    )

    app.add_url_rule(
        '/swagger/<endpoint_>',
        'swagger_schema',
        views.get_swagger_spec,
        methods=['GET'],
    )

    app.add_url_rule(
        '/geocode',
        'geocode',
        views.geocode,
        methods=['GET']
    )

    for operation, config in _path_map.items():
        path = config[0]
        endpoint = 'document_{}'.format(operation)
        func = config[1]
        options = {'methods': config[2]}

        logging.debug('Adding %s...', path)
        app.add_url_rule(path, endpoint, func, **options)


def _add_schema(app, json_file, force_security=False):
    endpoint = json_file.stem

    app.logger.info('Loading schema for endpoint %s from %s', endpoint, json_file)
    swagger_spec = load_schema(json_file)

    if force_security and not swagger_spec.get('security'):
        swagger_spec['security'] = swagger.DEFAULT_SECURITY_REQUIREMENTS

    app.schemastore.add_schema(endpoint, swagger_spec)

    return endpoint, swagger_spec

def load_schema(swagger_file):
    # type: (Path) -> dict

    with swagger_file.open() as swagger_json:
        specification = json.load(swagger_json, object_pairs_hook=OrderedDict)

    resolver = RefResolver(
        os.path.join(swagger_file.parent.absolute().as_uri(), ''),
        specification
    )
    resolved_specification = _resolve_refs(specification, resolver)

    # our schema files only contain `definitions`, so we copy them and add the
    # mandatory so we can use the swagger validation here
    valid_specification = {
        'swagger': '2.0',
        'info': {'version': '0.0', 'title': ''},
        'paths': {}
    }
    valid_specification.update(resolved_specification)

    validate_spec(valid_specification)

    return resolved_specification


def _resolve_refs(schema, resolver):
    if isinstance(schema, dict):
        ref = schema.get('$ref')
        if ref:
            return _resolve_refs(resolver.resolve(ref)[1], resolver)
        else:
            return OrderedDict([
                (key, _resolve_refs(value, resolver))
                for key, value in schema.items()
            ])
    elif isinstance(schema, list):
            return [_resolve_refs(element, resolver) for element in schema]
    else:
        return schema


def _add_template(app, json_file):
    template_name = json_file.stem

    app.logger.info('Loading template %s from %s', template_name, json_file)
    with json_file.open() as template_json:
        template = json.load(template_json)

    app.es.indices.put_template(name=template_name, body=template)


def configure_index(index, swagger_spec, non_resettable_settings, es):
    # type (str, dict, list, elasticsearch.Elasticsearch) -> None

    index_properties = swagger_spec.get('x-es-index', {})

    # make sure the index exists
    es.indices.create(
        index=index,
        body=index_properties,
        ignore=httplib.BAD_REQUEST
    )

    # blacklist non-resettable index settings
    resettable_settings = {
        setting: value for setting, value in index_properties.get('settings', {}).items()
        if setting not in non_resettable_settings
    }

    # put resettable settings
    if resettable_settings:
        es.indices.put_settings(index=index, body=resettable_settings)

    # put mappings configured on the index
    for doc_type, mapping in index_properties.get('mappings', {}).items():
        es.indices.put_mapping(index=index, doc_type=doc_type, body=mapping)


def configure_mappings(index, swagger_spec, es):
    # type (str, dict, elasticsearch.Elasticsearch) -> None
    assert es.indices.exists(index)

    for type_name, definition in swagger_spec.get('definitions', {}).items():
        configured_mapping = dict(definition.get('x-es-mapping', {}))

        unique_fields = list(definition.get('x-unique', []))
        for group in definition.get('x-unique-together', []):
            unique_fields.extend(group)

        if configured_mapping or unique_fields:
            current_mapping = es.indices.get_mapping(
                index=index
            )[index]['mappings'].get(type_name, {})

            current_mapping.update(configured_mapping)

            # create subfield for unique fields
            for field in unique_fields:
                _add_raw_subfield(
                    field,
                    current_mapping.get('properties', {}).get(field, {})
                )

            es.indices.put_mapping(
                index=index,
                doc_type=type_name,
                body=current_mapping
            )


def _add_raw_subfield(field, field_mapping):
    if 'type' not in field_mapping:
        raise ValueError(
            'You need to specify an ES `type` for field'
            ' `{}`'.format(field)
        )

    if 'fields' not in field_mapping:
        field_mapping['fields'] = {}

    if field_mapping['type'] == 'text':
        # mimic https://www.elastic.co/guide/en/elasticsearch/reference/current/breaking_50_mapping_changes.html#_default_string_mappings
        field_mapping['fields']['raw'] = {
            'type': 'keyword',
            'ignore_above': 256,
        }
    else:
        field_mapping['fields']['raw'] = {
            'type': field_mapping['type'],
            'index': 'not_analyzed'
        }


def _list_routes(app):
    # type: (flask.app.Flask) -> flask.app.Flask

    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)

        line = '{:50s} {:20s} {}'.format(rule.endpoint, methods, rule)
        output.append(line)

    logging.info('Application routes:')
    for line in sorted(output):
        logging.info(line)

    return app


def create_app(
    schema_path='schemas/',
    rest_subdir='indexes',
    template_subdir='templates',
):
    # type: (str, str, str) -> flask.app.Flask

    logging.basicConfig(level=logging.DEBUG)

    app = Flask(__name__)

    # Configure
    configure_app(app)

    @app.errorhandler(Exception)
    def jsonify_exceptions(error):
        # type: (Exception) -> flask.app.Response
        # TODO put in sentry/rollbar/airbrake
        app.logger.exception('Unhandled error: %s', error)

        try:
            # ES exception
            problem = error.info['error']['reason']
        except AttributeError:
            problem = error.message

        return views.error_response(500, problem)

    # Connect to Elasticsearch
    es = configure_elasticsearch(app)
    app.cluster = ClusterClient(es)
    app.datastore = DataStore(es)

    # Connect to Database
    from .database import db
    db.init_app(app)
    app.db = db

    with app.app_context():
        db.engine.execute('CREATE EXTENSION IF NOT EXISTS HSTORE')
        db.create_all()

    # Create Geocoder
    app.geocode = partial(GoogleV3().geocode, exactly_one=False)

    # Setup auth
    app.register_blueprint(auth)
    app.before_first_request(create_oauth_flow)
    app.before_request(authenticate_user)

    # Setup URL rules
    configure_endpoints(app)

    # Load schemas
    app.schemastore = SwaggerSchemaStore()

    schema_dir = Path(schema_path)
    rest_dir = schema_dir.joinpath(rest_subdir)
    template_dir = schema_dir.joinpath(rest_subdir, template_subdir)

    #  Non-REST endpoints
    for json_file in schema_dir.glob('*.json'):
        _add_schema(app, json_file)

    #  Load templates before configuring indexes
    for json_file in template_dir.glob('*.json'):
        _add_template(app, json_file)

    #  REST'ish indexes
    for json_file in rest_dir.glob('*.json'):
        index, swagger_spec = _add_schema(app, json_file, force_security=True)
        configure_index(
            index,
            swagger_spec,
            app.config['ELASTICSEARCH_NON_RESETTABLE_INDEX_SETTINGS'],
            es
        )
        configure_mappings(index, swagger_spec, es)

    _list_routes(app)

    app.logger.info('RelES reporting for duty...')

    return app
