# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from tempfile import gettempdir

from jsonschema import ValidationError
import pytest

from reles import configure_mappings
from reles.validators import  CustomDraft4Validator


class TestTheGeolocationValidator(object):

    @pytest.fixture
    def validator(self, datastore, test_index, test_doc_type):
        test_schema = {
            'type': 'object',
            'properties': {
                'geolocation': {
                    'type': 'object',
                    'x-check-geolocation': {
                        'address_field': 'postal_address',
                        'geopoint_field': 'geo_point',
                        'geopoint_deviation': 55,
                        'override_field': 'do_not_check',
                    },
                    'properties': {
                        'postal_address': {
                            'type': 'string'
                        },
                        'administrative_areas': {
                            'type': 'array',
                            'items': {'type': 'string'}
                        },
                        'geo_point': {
                            'type': 'string'
                        },
                        'do_not_check': {
                            'type': 'boolean',
                            'default': False,
                        }
                    }
                }
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

    def test_no_match(self, validator):
        with pytest.raises(ValidationError) as exception_info:
           validator.validate(
               {
                   'geolocation': {
                       'postal_address': 'this matches no address'
                   }
               }
           )

        assert '0 possible matches' in exception_info.value.message

    def test_not_unique(self, validator):
        with pytest.raises(ValidationError) as exception_info:
            # also matches 'Mühlendamm'
            validator.validate(
                {
                    'geolocation': {
                        'postal_address': 'Hamburg, Mühlenstr. 1'
                    }
                }
            )

        assert '2 possible matches' in exception_info.value.message

    def test_not_valid(self, validator):
        with pytest.raises(ValidationError) as exception_info:
            # match is of type 'route', not 'street_address'
            validator.validate(
                {
                    'geolocation': {
                        'postal_address': 'Hamburg, Mühlenstraße'
                    }
                }
            )

        assert 'not specific enough' in exception_info.value.message

    def test_do_not_check(self, validator):
        # does not raise since check has been overridden
        validator.validate(
            {
                'geolocation': {
                    'postal_address': 'this matches no address',
                    'do_not_check': True,
                }
            }
        )

    def test_no_address(self, validator):
        address_field = validator.schema['properties']['geolocation'] \
            ['x-check-geolocation']['address_field']

        with pytest.raises(ValidationError) as exception_info:
            validator.validate(
                {
                    'geolocation': {
                        'geo_point': '53.53, 9.99'
                    }
                }
            )

        assert address_field in exception_info.value.message
        assert 'required' in exception_info.value.message

    def test_no_geopoint(self, validator):
        # does not raise since geo point is not required
        validator.validate(
            {
                'geolocation': {
                    'postal_address': 'Hamburg, Mühlenstraße 1',
                }
            }
        )

    def test_geo_point_off(self, validator, app):
        max_deviation = validator.schema['properties']['geolocation'] \
            ['x-check-geolocation']['geopoint_deviation']

        address = 'Hamburg, Mühlenstraße 1'
        match = app.geocode(address, exactly_one=True)

        with pytest.raises(ValidationError) as exception_info:
            validator.validate(
                {
                    'geolocation': {
                        'postal_address': address,
                        'geo_point': '{}, {}'.format(
                            match.latitude - 0.00044,
                            match.longitude - 0.00044,
                        ),
                    }
                }
            )

        assert '(> {}) meters from matched location'.format(max_deviation) \
            in exception_info.value.message
