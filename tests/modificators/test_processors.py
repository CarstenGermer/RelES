import collections
from collections import defaultdict

import pytest

from reles.modificators import Processor
from .conftest import check_schema, validate


@pytest.fixture
def test_schema():
    schema = {
        'type': 'object',
        'id': 'instance',
        'properties': {
            'key1': {'type': 'string'},
            'key2': {'type': 'array', 'items': {'type': 'string'}},
            'key3': {
                'type': 'object',
                'properties': {
                    'key3key1': {'type': 'string'},
                    'key3key2': {'type': 'array', 'items': {'type': 'string'}},
                }
            },
            'reverse_me': {
                'type': 'string',
                'x-reverse': True,
            }
        }
    }

    return check_schema(schema)


@pytest.fixture
def processor(test_schema):
    def reverser(entity, schema, parent, context):
        if isinstance(entity, collections.Iterable):
            return entity[::-1]

    test_processors = {
        'x-reverse': reverser
    }

    return Processor(
        test_schema,
        datastore=defaultdict(dict),
        processors=test_processors
    )


def test_copies_everything(test_schema, processor):
    given = validate(
        test_schema,
        {
            'key1': 'value1',
            'key2': ['key2value1', 'key2value2', 'key2value3'],
            'key3': {
                'key3key1': 'key3key1value1',
                'key3key2': ['key3key2value1', 'key3key2value2', 'key3key2value3'],
            },
        }
    )

    processed = processor.process(given)

    assert given == processed


def test_reverser_gets_applied(test_schema, processor):
    given = validate(
        test_schema,
        {
            'reverse_me': 'hello world',
        }
    )

    processed = processor.process(given)

    assert processed['reverse_me'] == 'dlrow olleh'
