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
        'required': ['mandatory'],
        'properties': {
            'mandatory': {'type': 'string'},
            'optional': {'type': 'string'},
        }
    }

    return CustomDraft4Validator(
        test_schema,
        datastore=datastore,
        upload_path=gettempdir(),
    )


@pytest.fixture()
def int_validator(datastore):
    test_schema = {
        'type': 'object',
        'id': 'company',
        'required': ['mandatory'],
        'properties': {
            'mandatory': {'type': 'integer'},
            'optional': {'type': 'string'},
        }
    }

    return CustomDraft4Validator(
        test_schema,
        datastore=datastore,
        upload_path=gettempdir(),
    )


@pytest.mark.parametrize('mandatory,optional,message', [
    (None, 'i am here', "field 'mandatory' is required"),
    (None, None, "field 'mandatory' is required"),
    ('', 'i am here', "field 'mandatory' must not be empty"),
    ('', None, "field 'mandatory' must not be empty"),
    ([], 'i am here', "field 'mandatory' must not be empty"),
    ([], None, "field 'mandatory' must not be empty"),
    ({}, 'i am here', "field 'mandatory' must not be empty"),
    ({}, None, "field 'mandatory' must not be empty"),
])
def test_bad_values(validator, mandatory, optional, message):
    with pytest.raises(ValidationError) as e:
        # build doc without None values being set as such
        doc = {}
        if mandatory is not None:
            doc['mandatory'] = mandatory
        if optional is not None:
            doc['optional'] = optional

        validator.validate(doc)

    assert message in e.value.message


@pytest.mark.parametrize('mandatory,optional', [
    ('i am here', None),
    ('i am here', 'me too'),
])
def test_good_values(validator, mandatory, optional):
    # build doc without None values being set as such
    doc = {}
    if mandatory is not None:
        doc['mandatory'] = mandatory
    if optional is not None:
        doc['optional'] = optional

    # does not raise
    validator.validate(doc)


@pytest.mark.parametrize('mandatory,optional', [
    (0, None),
    (0, 'is a valid value'),
])
def test_falseish_integer(int_validator, mandatory, optional):
    # build doc without None values being set as such
    doc = {}
    if mandatory is not None:
        doc['mandatory'] = mandatory
    if optional is not None:
        doc['optional'] = optional

    # does not raise
    int_validator.validate(doc)
