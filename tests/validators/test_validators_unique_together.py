from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from random import randint
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
def random_age():
    return randint(0, 65536)


@pytest.fixture
def random_document(datastore, test_index, test_doc_type, random_name, random_age):
    return datastore.create_document(
        test_index,
        test_doc_type,
        {'name': random_name, 'age': random_age},
        refresh=True
    )


class TestValidatorUniqueTogether(object):
    @pytest.fixture
    def validator(self, datastore, test_index, test_doc_type):
        test_schema = {
            'type': 'object',
            'required': ['name', 'age'],
            'x-es-mapping': {
                'properties': {
                    'nickname': {'type': 'string'},
                    'name': {'type': 'string'},
                    'age': {'type': 'integer'},
                    'user': {'type': 'string'},
                    'host': {'type': 'string'},
                }
            },
            'x-unique-together': [
                ['name', 'age'],
                ['user', 'host']
            ],
            'x-unique': [
                'nickname',
            ],
            'properties': {
                'id': {'type': 'string'},
                'name': {'type': 'string'},
                'age': {'type': 'integer'},
                'user': {'type': 'string'},
                'host': {'type': 'string'},
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

    def test_create_no_conflict(self, validator, random_name, random_age):
        # does not raise (note also that `user` and `host` are absent, which is fine!)
        validator.validate({'name': random_name, 'age': random_age})

    def test_create_conflict_raises(self, validator, random_document):
        with pytest.raises(ValidationError) as e:
            validator.validate(
                {
                    'name': random_document['name'],
                    'age': random_document['age']
                }
            )

        assert 'unique property' in e.value.message
        assert 'conflicts with existing object' in e.value.message

    def test_create_missing_only_user_raises(self, validator, random_name, random_age):
        with pytest.raises(ValidationError) as e:
            validator.validate(
                {
                    'name': random_name,
                    'age': random_age,
                    'user': uuid4().hex,
                }
            )

        assert "needs all or none of it's fields" in e.value.message

    def test_create_missing_only_host_raises(self, validator, random_name, random_age):
        with pytest.raises(ValidationError) as e:
            validator.validate(
                {
                    'name': random_name,
                    'age': random_age,
                    'host': uuid4().hex,
                }
            )

        assert "needs all or none of it's fields" in e.value.message

    def test_update_no_conflict(self, validator, random_document):
        # does not raise
        validator.validate(
            {
                '_id': random_document['_id'],
                'name': random_document['name'],
                'age': random_document['age']
            }
        )

    def test_update_different_id_conflict_raises(self, validator, random_id, random_document):
        with pytest.raises(ValidationError) as e:
            validator.validate(
                {'id': random_id, 'name': random_document['name'], 'age': random_document['age']}
            )

        assert 'unique property' in e.value.message
        assert 'conflicts with existing object' in e.value.message

    def test_does_not_require_unique_individually(self, validator, random_document):
        # 'name' is not unique individually (but doesn't have to).
        # The changed 'age' makes the tuple unique together.
        validator.validate({
            'name': random_document['name'],
            'age': random_document['age'] + 1
        })
