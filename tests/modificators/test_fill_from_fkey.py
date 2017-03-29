from __future__ import absolute_import

from jsonschema import ValidationError
from mock import create_autospec
import pytest

from reles.modificators import Processor, _fill_from_fkey
from reles.persistence import DataStore
from .conftest import check_schema, validate


@pytest.fixture
def test_schema():
    schema = {
        'type': 'object',
        'id': 'instance',
        'properties': {
            'unprocessed': {'type': 'string'},
            'fkey_field': {
                'type': 'string',
                'x-fkey': {
                    'index': 'testIndex',
                    'doc_type': 'testDocType',
                },
            },
            'fkey_list': {
                'type': 'array',
                'items': {
                    'type': 'string',
                    'x-fkey': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                    }
                }
            },
            'nested_doc': {
                'type': 'object',
                'properties': {
                    'nested_fkey_field': {
                        'type': 'string',
                        'x-fkey': {
                            'index': 'testIndex',
                            'doc_type': 'testDocType',
                        }
                    }
                }
            },
            'nested_docs': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'nested_fkey_field': {
                            'type': 'string',
                            'x-fkey': {
                                'index': 'testIndex',
                                'doc_type': 'testDocType',
                            }
                        },
                        'nested_fkey_list': {
                            'type': 'array',
                            'items': {
                                'type': 'string',
                                'x-fkey': {
                                    'index': 'testIndex',
                                    'doc_type': 'testDocType',
                                }
                            },
                        },
                    }
                }
            },
            'filled_from_fkey': {
                'type': 'array',
                'items': {
                    'type': 'object'
                },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                    },
                    'fkey_field': 'fkey_field',
                },
            },
            'filled_from_fkey_field': {
                'type': 'array',
                'items': {
                    'type': 'string'
                },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                        'field': 'key1',
                    },
                    'fkey_field': 'fkey_field',
                },
            },
            'filled_from_fkey_list': {
                'type': 'array',
                'items': {
                    'type': 'object',
                 },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType'
                    },
                    'fkey_field': 'fkey_list'
                }
            },
            'filled_from_nested_fkey': {
                'type': 'array',
                'items': {
                    'type': 'object',
                },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                    },
                    'fkey_field': 'nested_doc.nested_fkey_field',
                }
            },
            'filled_from_nested_fkeys': {
                'type': 'array',
                'items': {
                    'type': 'object',
                },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                    },
                    'fkey_field': 'nested_docs.nested_fkey_field',
                }
            },
            'filled_from_nested_fkey_lists': {
                'type': 'array',
                'items': {
                    'type': 'object',
                },
                'x-fill-from-fkey': {
                    'source': {
                        'index': 'testIndex',
                        'doc_type': 'testDocType',
                    },
                    'fkey_field': 'nested_docs.nested_fkey_list',
                }
            }
        }
    }

    return check_schema(schema)


@pytest.fixture
def related_document():
    return {
        'key1': 'value1',
        'key2': ['key2value1', 'key2value2', 'key2value3'],
        'key3': {
            'key3key1': 'key3key1value1',
            'key3key2': ['key3key2value1', 'key3key2value2', 'key3key2value3'],
        },
    }


@pytest.fixture
def another_related_document():
    return {
        'key1': 'value11',
        'key2': ['key2value11', 'key2value21', 'key2value31'],
        'key3': {
            'key3key1': 'key3key1value11',
            'key3key2': ['key3key2value11', 'key3key2value21', 'key3key2value31'],
        },
    }

@pytest.fixture
def processor(test_schema, related_document, another_related_document):
    test_processors = {
        'x-fill-from-fkey': _fill_from_fkey
    }

    datastore = create_autospec(DataStore)
    datastore.get_document.side_effect = lambda index, doc_type, id: {
        'relatedFieldId': related_document,
        'anotherRelatedFieldId': another_related_document,
    }[id]

    return Processor(
        test_schema,
        datastore=datastore,
        processors=test_processors
    )


def test_fill_from_fkey_gets_applied(test_schema, processor, related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello world',
            'fkey_field': 'relatedFieldId',
        }
    )

    processed = processor.process(given)

    assert processed['unprocessed'] == 'hello world'

    assert processed['filled_from_fkey'] == [related_document]
    assert processed['filled_from_fkey_field'] == ['value1']


def test_fill_from_fkey_works_on_arrays(test_schema, processor, related_document, another_related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello world',
            'fkey_list': ['relatedFieldId', 'anotherRelatedFieldId']
        }
    )

    processed = processor.process(given)

    assert processed['unprocessed'] == 'hello world'
    assert processed['filled_from_fkey_list'] == [related_document, another_related_document]


def test_fill_from_fkey_works_on_a_nested_doc(test_schema, processor, related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello_world',
            'nested_doc': {
                'nested_fkey_field': 'relatedFieldId'
            }
        }
    )

    processed = processor.process(given)

    assert processed['unprocessed'] == 'hello_world'
    assert processed['filled_from_nested_fkey'] == [related_document]


def test_fill_from_fkey_works_on_a_list_of_nested_docs(test_schema, processor, related_document, another_related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello_world',
            'nested_docs': [
                {
                    'nested_fkey_field': 'relatedFieldId'
                },
                {
                    'nested_fkey_field': 'anotherRelatedFieldId'
                },
            ]
        }
    )

    processed = processor.process(given)

    assert processed['unprocessed'] == 'hello_world'
    assert processed['filled_from_nested_fkeys'] == [related_document, another_related_document]


def test_fill_from_fkey_flattens_a_list_of_nested_fkey_lists(test_schema, processor, related_document, another_related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello_world',
            'nested_docs': [
                {
                    'nested_fkey_list': ['relatedFieldId']
                },
                {
                    'nested_fkey_list': ['anotherRelatedFieldId']
                },
            ]
        }
    )

    processed = processor.process(given)

    assert processed['unprocessed'] == 'hello_world'
    assert processed['filled_from_nested_fkey_lists'] == [related_document, another_related_document]


def test_entity_must_not_be_set_already(test_schema, processor, related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello world',
            'fkey_field': 'relatedFieldId',
            'filled_from_fkey': [{'someKindOf': 'Document'}]
        }
    )

    with pytest.raises(ValidationError) as e:
        processor.process(given)

    assert 'entity can not be set' in e.value.message


def test_entity_must_not_be_set_field(test_schema, processor, related_document):
    given = validate(
        test_schema,
        {
            'unprocessed': 'hello world',
            'fkey_field': 'relatedFieldId',
            'filled_from_fkey_field': ['presetValue']
        }
    )

    with pytest.raises(ValidationError) as e:
        processor.process(given)

    assert 'entity can not be set' in e.value.message


def test_copes_with_missing_fkey_field(test_schema, processor):
    # no document referenced to be denormalized
    unprocessed = {
        'unprocessed': 'hello world'
    }

    given = validate(
        test_schema,
        unprocessed,
    )

    # does not raise
    processed = processor.process(given)

    # the processor doesn't touch the document if there is nothing to denormalize
    assert processed == unprocessed
