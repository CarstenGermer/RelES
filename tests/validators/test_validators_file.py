from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from os import path
from tempfile import NamedTemporaryFile, gettempdir
from uuid import uuid4

from jsonschema import ValidationError
import pytest

from reles.validators import CustomDraft4Validator


@pytest.yield_fixture
def existing_file_name():
    with NamedTemporaryFile() as f:
        yield f.name


class TestValidatorFile(object):
    @pytest.fixture
    def validator(self, datastore):
        test_schema = {
            'type': 'object',
            'required': ['sys_filename', ],
            'properties': {
                'sys_filename': {
                    'type': 'string',
                    'x-file': True
                }
            }
        }

        return CustomDraft4Validator(
            test_schema,
            datastore=datastore,
            upload_path=gettempdir(),
        )

    def test_missing_file(self, validator):
        with pytest.raises(ValidationError) as e:
            validator.validate({'sys_filename': uuid4().hex})

        assert 'invalid file referenced' in e.value.message

    def test_success(self, validator, existing_file_name):
        validator.validate({'sys_filename': path.basename(existing_file_name)})
