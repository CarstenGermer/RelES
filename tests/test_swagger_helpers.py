from __future__ import absolute_import

from mock import Mock
import pytest
from swagger_spec_validator.validator20 import validate_spec

from reles import _resolve_refs
from reles.swagger import (
    _build_definitions,
    _build_parameters,
    _build_paths,
    _build_responses,
    _build_tags,
    build_swagger_json,
)


@pytest.fixture
def schema():
    return (
        'testIndex',
        {
            'security': [],
            'definitions':
            {
                'testDoctype': {
                    'type': 'object',
                    'properties': {
                        'title': {'type': 'string'}
                    }
                }
            }
        }
    )


@pytest.fixture
def referencing_schema():
    return (
        'testIndex',
        {
            'testDoctype': {
                'type': 'object',
                'properties': {
                    'title': {'type': 'string'},
                    'reles': {'$ref': 'snippets/reles.json'}
                }
            }
        }
    )


@pytest.fixture
def reles_snippet():
    return (
        'file:///path/to/snippets/reles.json',
        {
            'type': 'object',
            'properties': {
                'created_by': {'$ref': 'snippets/user.json'},
                'created_at': {'$ref': 'snippets/timestamp.json'}
            }
        }
    )


@pytest.fixture
def user_snippet():
    return (
        'file:///path/to/snippets/user.json',
        {
            'type': 'object',
            'properties': {
                'full_name': {'type': 'string'},
            }
        }
    )


@pytest.fixture
def timestamp_snippet():
    return (
        'file:///path/to/snippets/timestamp.json',
        {
            'type': 'object',
            'properties': {
                'date': {'type': 'string'},
                'time': {'type': 'string'}
            }
        }
    )


def test_build_definitions(schema):
    index, reference_definitions = schema[0], schema[1]['definitions']

    definitions = _build_definitions(reference_definitions)

    for doc_type, doc_spec in reference_definitions.items():
        assert doc_type in definitions
        assert doc_spec == definitions[doc_type]

    assert 'errorModel' in definitions
    assert 'properties' in definitions['errorModel']
    assert 'message' in definitions['errorModel']['properties']


def test_build_parameters():
    parameters = _build_parameters()

    # might contain more,  but `id` is mandatory for basic functionality
    assert 'id' in parameters
    id_param = parameters['id']
    assert 'in' in id_param
    assert id_param['in'] == 'path'
    assert 'required' in id_param
    assert id_param['required'] is True


def test_build_paths(schema):
    def _assert_collection_path(collection_path, paths):
        assert 'get' in paths[collection_path]
        assert 'responses' in paths[collection_path]['get']
        assert '200' in paths[collection_path]['get']['responses']
        assert 'default' in paths[collection_path]['get']['responses']

        assert 'post' in paths[collection_path]
        assert 'responses' in paths[collection_path]['post']
        assert '201' in paths[collection_path]['post']['responses']
        assert 'default' in paths[collection_path]['post']['responses']

    def _assert_document_path(document_path, paths):
        assert 'get' in paths[document_path]
        assert 'responses' in paths[document_path]['get']
        assert '200' in paths[document_path]['get']['responses']
        assert 'default' in paths[document_path]['get']['responses']

        assert 'put' in paths[document_path]
        assert 'responses' in paths[document_path]['put']
        assert '200' in paths[document_path]['put']['responses']
        assert 'default' in paths[document_path]['put']['responses']

        assert 'parameters' in paths[document_path]
        assert {'$ref': '#/parameters/id'} in paths[document_path]['parameters']

    index, definitions = schema[0], schema[1]['definitions']

    paths = _build_paths(index, definitions)

    for doc_type in definitions.keys():
        collection_path = '/{}/{}/'.format(index, doc_type)
        assert collection_path in paths
        _assert_collection_path(collection_path, paths)

        document_path = '/{}/{}/{{id}}'.format(index, doc_type)
        assert document_path in paths
        _assert_document_path(document_path, paths)


def test_build_responses():
    responses = _build_responses()

    # might contain more, but these are mandatory for basic functionality
    assert 'forbidden' in responses
    assert 'genericError' in responses
    assert 'unauthorized' in responses


def test_build_tags(schema):
    index, definitions = schema[0], schema[1]['definitions']

    paths = _build_paths(index, definitions)
    tags = _build_tags(paths)

    assert {'name': index} in tags

    for doc_type in definitions.keys():
        assert {'name': doc_type} in tags


def test_build_swagger_json(schema):
    index, spec = schema

    app = Mock()
    app.schemastore._schemas = {index: spec}

    swagger_spec = build_swagger_json(index, spec)

    # does not raise
    validate_spec(swagger_spec)


def test_resolve_refs(referencing_schema, reles_snippet, user_snippet, timestamp_snippet):
    # Setup mock resolver
    def resolve(value):
        if 'reles' in value:
            return reles_snippet
        elif 'user' in value:
            return user_snippet
        elif 'timestamp' in value:
            return timestamp_snippet
        else:
            return {'ERROR': 'Unexpected snippet \'%s\' requested' % value}

    index, definitions = referencing_schema

    resolver = Mock()
    resolver.resolve.side_effect=resolve

    # Test
    resolved_schema = _resolve_refs(definitions, resolver)

    # Check result
    expected_schema = dict(definitions)
    expected_schema['testDoctype']['properties']['reles'] = dict(reles_snippet[1])
    expected_schema['testDoctype']['properties']['reles']['properties']['created_by'] = dict(user_snippet[1])
    expected_schema['testDoctype']['properties']['reles']['properties']['created_at'] = dict(timestamp_snippet[1])

    assert resolved_schema == expected_schema
