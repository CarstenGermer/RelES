# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from jsonschema import ValidationError
from mock import create_autospec
import pytest

from reles.modificators import Processor, _include_parents
from reles.persistence import DataStore
from .conftest import check_schema, validate


@pytest.fixture
def test_schema():
    schema = {
        'type': 'object',
        'properties': {
            'name': {'type': 'string'},
            'children': {
                'type': 'array',
                'items': {
                    'type': 'number',
                },
                'x-include-parents': {
                    'index': 'testIndex',
                    'doc_type': 'testDocType',
                    'parent_field': 'parent'
                }
            }
        }
    }

    return check_schema(schema)


@pytest.fixture
def datastore():
    docs = {
        0: {},             #       0
        1: {'parent': 0},  #      / \
        2: {'parent': 0},  #     1  2
        3: {'parent': 2},  #       / \
        4: {'parent': 2},  #      3  4
        5: {'parent': 3},  #     / \  \
        6: {'parent': 3},  #    5  6  7
        7: {'parent': 4},  #        \
        8: {'parent': 6},  #        8
    }

    datastore = create_autospec(DataStore, spec_set=True, instance=True)
    datastore.get_document.side_effect = lambda idx, dt, id: docs[id]

    return datastore


@pytest.fixture
def processor(test_schema, datastore):

    test_processors = {
        'x-include-parents': _include_parents
    }

    return Processor(
        test_schema,
        datastore=datastore,
        processors=test_processors
    )


class TestTheIncludeParentsModifier(object):
    def test_expands_children(self, test_schema, processor):
        given = validate(
            test_schema,
            {
                'name': 'brangelina',
                'children': [6, 4]
            }
        )

        processed = processor.process(given)

        assert len(processed) == len(given)
        assert processed['name'] == given['name']
        assert processed['children'] == [0, 2, 3, 4, 6]

    def test_handles_missing_fields(self, test_schema, processor):
        given = validate(
            test_schema,
            {
                'name': 'brangelina'
            }
        )

        processed = processor.process(given)

        assert processed == given
