from tempfile import gettempdir

from jsonschema import ValidationError
import pytest

from reles.persistence import DataStore
from reles.validators import CustomDraft4Validator

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


@pytest.fixture()
def datastore():
    return Mock(DataStore)


class TestValidatorEnum(object):
    @pytest.fixture()
    def validator(self, datastore):
        test_schema = {
            'type': 'object',
            'required': ['smoking'],
            'properties': {
                'smoking': {
                    'enum': ['allowed', 'forbidden', 'seperate_room', '5'],

                }
            }
        }

        return CustomDraft4Validator(
            test_schema,
            datastore=datastore,
            upload_path=gettempdir(),
        )

    def test_bad_value(self, validator):
        with pytest.raises(ValidationError) as e:
            validator.validate({'smoking': 'cool'})

        assert "'cool' is not one of" in e.value.message

    def test_not_casting_to_string(self, validator):
        with pytest.raises(ValidationError) as e:
            validator.validate({'smoking': 5})

        assert "5 is not one of" in e.value.message
