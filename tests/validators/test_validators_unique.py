from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from tempfile import gettempdir
from uuid import uuid4

from jsonschema import ValidationError
import pytest

from reles import configure_mappings
from reles.validators import CustomDraft4Validator


@pytest.fixture
def random_name():
    return uuid4().hex


@pytest.fixture
def random_name_document(datastore, test_index, test_doc_type, random_name):
    return datastore.create_document(
        test_index,
        test_doc_type,
        {'name': random_name},
        refresh=True
    )


class TestValidatorUnique(object):
    @pytest.fixture
    def validator(self, datastore, test_index, test_doc_type):
        test_schema = {
            'type': 'object',
            'required': ['name', ],
            'x-es-mapping': {
                'properties': {
                    'name': {'type': 'string'},
                    'nickname': {'type': 'string'},
                }
            },
            'x-unique': ['name', 'nickname'],
            'properties': {
                'id': {'type': 'string'},
                'name': {'type': 'string'},
            }
        }

        configure_mappings(
            test_index,
            {'definitions': {test_doc_type: test_schema}},
            datastore._es
        )

        return CustomDraft4Validator(
            test_schema,
            datastore=datastore,
            upload_path=gettempdir(),
            index=test_index,
            doc_type=test_doc_type
        )

    def test_create_no_conflict(self, validator, random_name):
        # does not raise (note also that `nickname` is absent, which is fine!)
        validator.validate({'name': random_name})

    def test_create_conflict_raises(self, validator, random_name_document):
        with pytest.raises(ValidationError) as e:
            validator.validate({'name': random_name_document['name']})

        assert 'unique property' in e.value.message
        assert 'conflicts with existing object' in e.value.message

    def test_update_no_conflict(self, validator, random_name_document):
        # does not raise
        validator.validate(
            {'_id': random_name_document['_id'], 'name': random_name_document['name']}
        )

    def test_update_conflict_raises(self, validator, random_id, random_name_document):
        with pytest.raises(ValidationError) as e:
            validator.validate({'id': random_id, 'name': random_name_document['name']})

        assert 'unique property' in e.value.message
        assert 'conflicts with existing object' in e.value.message
