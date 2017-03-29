# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals


from flask import Flask
from jsonschema import ValidationError
from mock import create_autospec
import pytest

from reles import DataStore, modificators
from reles.modificators import Processor, _log_access
from .conftest import check_schema, validate


@pytest.fixture
def test_schema():
    schema = {
        "type": "object",
        "x-es-mapping": {
            "properties": {
                "log": {
                    "created": { "type": "date" },
                    "changed": { "type": "date" },
                    "editor": {
                        "type": "string",
                        "index": "not_analyzed"
                    },
                    "customer": {
                        "type": "string",
                        "index": "not_analyzed"
                    }
                }
            }
        },
        "properties": {
            "log": {
                "type": "object",
                "x-log-access": {
                    "created": "created",
                    "updated": "changed",
                    "user": "editor",
                    "customer": "customer"
                },
                "properties": {
                    "created": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "changed": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "editor": {
                        "type": "string",
                        "format": "uuid",
                        "x-fkey": {
                            "index": "auth",
                            "doc_type": "user"
                        }
                    },
                    "customer": {
                        "type": "string",
                        "format": "uuid",
                        "x-fkey": {
                            "index": "auth",
                            "doc_type": "customer"
                        }
                    }

                }
            },
            "name": {
                "type": "string"
            }
        }
    }

    return check_schema(schema)


@pytest.fixture
def modification_time():
    return 598997700


@pytest.yield_fixture
def g(monkeypatch, modification_time):
    app = Flask(__name__)
    ctx = app.app_context()

    ctx.g.user = {'email': 'john.mcclane@nyc.gov'}
    ctx.g.customer = {'name': 'NYPD'}

    monkeypatch.setattr(modificators, 'time', lambda: modification_time)

    with ctx:
        yield ctx.g


@pytest.fixture
def processor(test_schema):

    test_processors = {
        'x-log-access': _log_access
    }

    datastore = create_autospec(DataStore)

    return Processor(
        test_schema,
        datastore=datastore,
        processors=test_processors
    )


def test_creation_gets_logged(test_schema, processor, g, modification_time):
    name = 'Nakatomi Plaza'

    given = validate(
        test_schema,
        {
            'name': name
        }
    )

    processed = processor.process(given)

    assert processed == {
        'log': {
            'created': modification_time,
            'editor': g.user['email'],
            'customer': g.customer['name'],
        },
        'name': name
    }


def test_update_gets_logged(test_schema, processor, g, modification_time):
    name = 'Dulles International Airport'

    given = validate(
        test_schema,
        {
            'name': name
        }
    )

    processed = processor.process(given, id=1)

    assert processed == {
        'log': {
            'changed': modification_time,
            'editor': g.user['email'],
            'customer': g.customer['name'],
        },
        'name': name
    }


def test_manual_override_is_rejected(test_schema, processor):
    given = validate(
        test_schema,
        {
            'name': 'New York',
            'log': {
                'editor': 'simon@gruber.net'
            }
        }
    )

    with pytest.raises(ValidationError) as exception_info:
        processor.process(given, id=1)

    assert 'cannot be overridden manually' in exception_info.value.message
