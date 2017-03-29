from __future__ import absolute_import, unicode_literals

from json import loads
import time

from flask import Flask, make_response
from jose import jwt
from mock import Mock
import pytest

from reles.auth import middleware, utils


_TEST_AUTH_JWT_ALGORITHM = 'HS512'
_TEST_JWT_SECRET = b'SECRET'
_TEST_TOKEN_ISSUER = 'testtesttest'
_TEST_TOKEN_LIFETIME = 3600


@pytest.fixture()
def app():
    _app = Flask(__name__)
    _app.config['AUTH_JWT_ALGORITHM'] = _TEST_AUTH_JWT_ALGORITHM
    _app.config['AUTH_JWT_SECRET'] = _TEST_JWT_SECRET
    _app.config['AUTH_TOKEN_ISSUER'] = _TEST_TOKEN_ISSUER
    _app.config['AUTH_TOKEN_LIFETIME'] = _TEST_TOKEN_LIFETIME
    _app.config['UNAUTHENTICATED_VIEWS'] = ['insecure', ]

    @_app.route('/insecure')
    def insecure():
        return make_response("you've reached: insecure")

    @_app.route('/secure')
    def secure():
        return make_response("you've reached: secure")

    _app.before_request(middleware.authenticate_user)

    return _app


@pytest.yield_fixture()
def test_client(app):
    with app.app_context():
        yield app.test_client()


@pytest.fixture()
def sessionized_user():
    return {
        '_id': 'rAGnAr',
        'google_name': 'Ragnar Lothbrok',
        'email': 'ragnar@kattegat.dk',
        'customers': ['kattegat'],
    }


@pytest.fixture()
def sessionized_customer():
    return {
        '_id': 'kAttEGAt',
        'name': 'kattegat',
        'permissions': {},
    }


@pytest.fixture()
def login_required(monkeypatch):
    monkeypatch.setattr(middleware, 'login_required', lambda: True)


@pytest.fixture()
def no_login_required(monkeypatch):
    monkeypatch.setattr(middleware, 'login_required', lambda: False)


@pytest.fixture()
def valid_jwt(sessionized_user, sessionized_customer):
    return utils.format_jwt(sessionized_user, sessionized_customer, False)


@pytest.fixture()
def expired_jwt(sessionized_user, sessionized_customer, monkeypatch):
    monkeypatch.setattr(
        utils,
        'time',
        Mock(**{
            'time.return_value': int(time.time()) - _TEST_TOKEN_LIFETIME - 1
        })
    )

    return utils.format_jwt(sessionized_user, sessionized_customer, False)


@pytest.fixture()
def malsigned_jwt(sessionized_user, sessionized_customer, app):
    fake_key = 'AAAA'
    valid_key = app.config['AUTH_JWT_SECRET']

    app.config['AUTH_JWT_SECRET'] = fake_key
    jwt = utils.format_jwt(sessionized_user, sessionized_customer, False)
    app.config['AUTH_JWT_SECRET'] = valid_key

    return jwt


def test_insecure_no_auth_header_is_200(test_client, no_login_required):
    # type: (flask.testing.FlaskClient) -> None

    res = test_client.get('/insecure')
    assert res.status_code == 200
    assert 'reached: insecure' in res.data


def test_insecure_valid_auth_header_is_200(test_client, valid_jwt, no_login_required):
    # type: (flask.testing.FlaskClient) -> None

    headers = {
        'Authorization': 'Bearer {}'.format(valid_jwt)
    }

    res = test_client.get('/insecure', headers=headers)
    assert res.status_code == 200
    assert 'reached: insecure' in res.data


def test_secure_no_auth_header_is_401(test_client, login_required):
    # type: (flask.testing.FlaskClient) -> None

    res = test_client.get('/secure')
    assert res.status_code == 401


def test_secure_valid_auth_header_is_200(test_client, valid_jwt, login_required):
    # type: (flask.testing.FlaskClient) -> None

    headers = {
        'Authorization': 'Bearer {}'.format(valid_jwt)
    }

    res = test_client.get('/secure', headers=headers)
    assert res.status_code == 200
    assert 'reached: secure' in res.data


def test_secure_only_non_bearer_auth_header_is_401(test_client, valid_jwt, login_required):
    # type: (flask.testing.FlaskClient) -> None

    headers = {
        'Authorization': 'NonBearer {}'.format(valid_jwt)
    }

    res = test_client.get('/secure', headers=headers)
    assert res.status_code == 401


def test_secure_malformed_jwt_is_401(test_client, valid_jwt, login_required):
    headers = {
        'Authorization': 'Bearer {}'.format(valid_jwt[:-1])
    }

    res = test_client.get('/secure', headers=headers)
    assert res.status_code == 401


def test_secure_malsigned_jwt_is_401(test_client, malsigned_jwt, login_required):
    headers = {
        'Authorization': 'Bearer {}'.format(malsigned_jwt)
    }

    res = test_client.get('/secure', headers=headers)
    assert res.status_code == 401


def test_secure_expired_jwt_is_401(test_client, expired_jwt, login_required):
    headers = {
        'Authorization': 'Bearer {}'.format(expired_jwt)
    }

    res = test_client.get('/secure', headers=headers)
    assert res.status_code == 401
    assert 'expired' in loads(res.data)['message']
