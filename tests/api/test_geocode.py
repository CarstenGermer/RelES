# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

import httplib

from flask import url_for
import pytest


@pytest.mark.usefixtures('live_server')
class TestTheGeocodeEndpoint(object):

    def test_no_match(self, requests):
        response = requests.get(
            url_for('geocode', _external=True),
            params={'address': 'This matches no address'},
        )

        assert response.json() == []

    def test_no_valid_match(self, requests):
        response = requests.get(
            url_for('geocode', _external=True),
            params={'address': 'Hamburg, Mühlenstraße'},
        )

        assert response.json() == []

    def test_exactly_one_match(self, requests):
        address = 'Hamburg, Mühlenstraße 1'

        matches = requests.get(
            url_for('geocode', _external=True),
            params={'address': address},
        ).json()

        assert isinstance(matches, list)
        assert len(matches) == 1

        for match in matches:
            # check syntax
            assert 'formatted_address' in match
            assert 'administrative_areas' in match
            assert 'lat' in match
            assert 'lon' in match

            # spot check semantics
            assert all(
                [
                    part.strip(',') in match['formatted_address']
                    for part in address.split()
                ]
            )
            assert all(
                [
                    admin in match['administrative_areas']
                    for admin in ['Hamburg', 'HH', 'Germany', 'DE']
                    ]
            )

    def test_multiple_matches(self, requests):
        # also matches 'Mühlendamm 1'
        address = 'Hamburg, Mühlenstr. 1'

        matches = requests.get(
            url_for('geocode', _external=True),
            params={'address': address},
        ).json()

        assert len(matches) == 2
        for match in matches:
            # check syntax
            assert 'formatted_address' in match
            assert 'administrative_areas' in match
            assert 'lat' in match
            assert 'lon' in match

    def test_charging(self, requests, customer, app):
        assert 'cycles' not in customer

        response = requests.get(
            url_for('geocode', _external=True),
            params={'address': 'Hamburg, Mühlenstraße 1'},
        )

        assert response.status_code == httplib.OK

        customer.refresh()

        assert len(customer.cycles.to_dict()) == 1
        assert customer.cycles['_geocode_address'] == app.config['CYCLES_GEOCODING']

    def test_charging_on_failure(self, requests, customer):
        assert 'cycles' not in customer

        no_address = ''

        response = requests.get(
            url_for('geocode', _external=True),
            params={'address': no_address},
        )

        assert response.status_code == httplib.BAD_REQUEST

        customer.refresh()

        assert 'cycles' not in customer
