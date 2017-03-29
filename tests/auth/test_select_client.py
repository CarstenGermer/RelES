# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from flask import url_for
import httplib
from jose import jwt
import pytest


@pytest.mark.usefixtures('live_server')
class TestTheSelectCustomerEndpoint(object):

    def test_handles_missing_customer_parameter(self, requests):
        response = requests.get(
            url_for('auth.activate_customer', _external=True),
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert response.json()['message'] == 'specify a customer to set as active'

    def test_handles_invalid_customers(self, requests):
        response = requests.get(
            url_for('auth.activate_customer', _external=True),
            params={'customer': 'league of justice'}
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert response.json()['message'] == 'invalid customer'

    def test_activates_a_valid_customer(self, app, valid_jwt, customer, another_customer, requests):
        original_token = jwt.decode(valid_jwt, app.config['AUTH_JWT_SECRET'])
        assert original_token['active_customer']['name'] == customer.name
        assert another_customer.name in original_token['user']['customers']

        response = requests.get(
            url_for('auth.activate_customer', _external=True),
            params={'customer': another_customer.name}
        )

        assert response.status_code == httplib.OK
        assert response.headers['Content-Type'] == 'application/jwt'

        updated_token = jwt.decode(response.content, app.config['AUTH_JWT_SECRET'])
        assert updated_token['active_customer']['name'] == another_customer.name

        del original_token['active_customer']
        del updated_token['active_customer']
        assert updated_token == original_token
