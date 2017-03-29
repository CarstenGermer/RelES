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


@pytest.fixture()
def validator(datastore):
    test_schema = {
        'type': 'object',
        'id': 'company',
        'properties': {
            'tags': {
                'type': 'array',
                'items': {'type': 'string'},
                'minItems': 1,
                'uniqueItems': True,
            },
            'flags': {
                'type': 'array',
                'items': {'type': 'integer'},
                'maxItems': 3,
            },
        }
    }

    return CustomDraft4Validator(
        test_schema,
        datastore=datastore,
        upload_path=gettempdir(),
    )


@pytest.mark.parametrize('tags,flags,message', [
    (None, None, "is not of type 'array'"),
    ('', '', "is not of type 'array'"),
    ('', [], "is not of type 'array'"),
    ([], '', "is not of type 'array'"),
    ([1], '', "is not of type 'array'"),
    ([], [], 'is too short'),
    (['tag1', 'tag1'], [], 'has non-unique elements'),
    (['tag1'], ['1'], "is not of type 'integer'"),
    (['tag1'], [1, 2, 3, 4], 'is too long'),
])
def test_bad_values(validator, tags, flags, message):
    with pytest.raises(ValidationError) as e:
        validator.validate({'tags': tags, 'flags': flags})

    if message:
        assert message in e.value.message


@pytest.mark.parametrize('tags,flags', [
    (['tag1'], []),
    (['tag1', 'tag2', 'tag3', 'tag4'], [1, 2, 3]),
])
def test_good_values(validator, tags, flags):
    # does not raise
    validator.validate({'tags': tags, 'flags': flags})
