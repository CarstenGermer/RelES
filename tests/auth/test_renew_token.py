# coding: utf-8


from __future__ import absolute_import, print_function, unicode_literals


from flask import url_for
import httplib
from jose import jwt
import pytest
import requests


@pytest.mark.usefixtures('live_server')
class TestTheTokenRenewalEndpoint(object):

    def test_handles_an_invalid_user(self, renewable_jwt, user):
        user.delete(refresh=True)

        response = requests.get(
            url_for('auth.renew_token', _external=True),
            headers={'Authorization': 'Bearer %s' % renewable_jwt}
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert 'no user with email' in response.json()['message']

    def test_rejects_non_renewable_tokens(self, valid_jwt):
        response = requests.get(
            url_for('auth.renew_token', _external=True),
            headers={'Authorization': 'Bearer %s' % valid_jwt}
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert 'not renewable' in response.json()['message']

    def test_renews_an_eligible_token(self, renewable_jwt, app):
        original_token = jwt.decode(
            renewable_jwt,
            app.config['AUTH_JWT_SECRET']
        )

        response = requests.get(
            url_for('auth.renew_token', _external=True),
            headers={'Authorization': 'Bearer %s' % renewable_jwt}
        )

        new_token = jwt.decode(response.text, app.config['AUTH_JWT_SECRET'])

        assert response.status_code == httplib.OK
        assert new_token['user'] == original_token['user']
        assert new_token['active_customer'] == original_token['active_customer']
        assert new_token['renewable'] == original_token['renewable']
        assert new_token['exp'] > original_token['exp']
