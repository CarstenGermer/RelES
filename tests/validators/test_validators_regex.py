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
        'required': ['name'],
        'properties': {
            'name': {
                'type': 'string',
                'pattern': 'into[A-Z]\w*',
            }
        }
    }

    return CustomDraft4Validator(
        test_schema,
        datastore=datastore,
        upload_path=gettempdir(),
    )


@pytest.mark.parametrize('company_name', [
    'outofSite',
    'Google',
    'faceBook',
    'agilebunch',
    'intolowercase',
    'IntoCapitalized',
])
def test_bad_values(validator, company_name):
    with pytest.raises(ValidationError) as e:
        validator.validate({'name': company_name})

    assert "'{}' does not match".format(company_name) in e.value.message


@pytest.mark.parametrize('company_name', [
    'intoSite',
    'intoOffice',
    'intoLabs',
    'intoFitness',
])
def test_good_values(validator, company_name):
    # does not raise
    validator.validate({'name': company_name})
