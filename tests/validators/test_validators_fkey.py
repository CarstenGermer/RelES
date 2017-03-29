from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from tempfile import gettempdir
from uuid import uuid4

from elasticsearch.exceptions import NotFoundError
from jsonschema import ValidationError
import pytest

from reles.validators import CustomDraft4Validator


class TestValidatorFkey(object):
    @pytest.fixture()
    def validator(self, datastore, test_index, test_doc_type):
        test_schema = {
            'type': 'object',
            'required': ['parent_id', ],
            'properties': {
                'parent_id': {
                    'type': 'string',
                    'fkey': {
                        'index': test_index,
                        'doc_type': test_doc_type,
                    }
                }
            }
        }

        return CustomDraft4Validator(
            test_schema,
            datastore=datastore,
            upload_path=gettempdir(),
        )

    def test_missing_document(self, validator, datastore, test_index, test_doc_type, random_id):
        # the document does not exist
        with pytest.raises(NotFoundError):
            datastore.get_document(test_doc_type, test_index, random_id)

        with pytest.raises(ValidationError) as e:
            validator.validate({'parent_id': random_id})

        assert 'Invalid foreign key: no such document' in e.value.message

    def test_success(self, validator, datastore, test_index, test_doc_type, random_id):
        datastore.create_document(test_index, test_doc_type, {'key1': 'value1'}, random_id)

        # does not raise:
        validator.validate({'parent_id': random_id})


class TestValidatorFkeyArray(object):
    @pytest.fixture()
    def validator_array_items(self, datastore, test_index, test_doc_type):
        schema = {
            'type': 'object',
            'required': ['parents', ],
            'properties': {
                'parents': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'fkey': {
                            'index': test_index,
                            'doc_type': test_doc_type,
                        }
                    },

                }
            },
        }

        return CustomDraft4Validator(
            schema,
            datastore=datastore,
            upload_path=gettempdir(),
        )

    def test_success_array_items(
        self,
        validator_array_items,
        datastore,
        test_index,
        test_doc_type,
        random_id
    ):
        datastore.create_document(test_index, test_doc_type, {'key1': 'value1'}, random_id)

        # does not raise:
        validator_array_items.validate({'parents': [random_id]})

    def test_array_items_missing_any_fails(
        self,
        validator_array_items,
        datastore,
        test_index,
        test_doc_type,
        random_id
    ):
        hit_document_id = random_id
        miss_document_id = uuid4().hex

        datastore.create_document(test_index, test_doc_type, {'key1': 'value1'}, hit_document_id)

        with pytest.raises(ValidationError) as e:
            validator_array_items.validate({'parents': [hit_document_id, miss_document_id]})

        assert 'Invalid foreign key: no such document' in e.value.message
