# coding: utf-8

"""Test the login process."""

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import httplib
from urlparse import parse_qs, urlsplit
from uuid import uuid4

from flask import Flask, url_for
from mock import Mock
import pytest
import requests

from reles.auth import views as auth_views
from reles.auth.exceptions import ConflictError
from reles.auth.models import User
from reles.auth.utils import set_params


@pytest.yield_fixture(scope='function')
def test_client():
    app = Flask(__name__)
    app.debug = True
    app.testing = True
    app.config['SECRET_KEY'] = uuid4().hex
    app.config['AUTH_JWT_ALGORITHM'] = 'HS512'
    app.config['AUTH_JWT_SECRET'] = uuid4().hex
    app.config['AUTH_TOKEN_LIFETIME'] = 3600
    app.config['AUTH_TOKEN_ISSUER'] = uuid4().hex

    from reles.auth.views import auth
    app.register_blueprint(auth)

    ctx = app.test_request_context()
    with app.app_context():
        ctx.push()
        yield app.test_client()
        ctx.pop()


@pytest.fixture(scope='function')
def csrf_token(test_client):
    """Inject a CSRF token into the session."""
    with test_client.session_transaction() as session:
        session['state'] = uuid4().hex
        return session['state']


@pytest.fixture(scope='function')
def authenticated_email(test_client, monkeypatch):
    """Inject credentials into the oauth process."""
    email = '%s@example.com' % uuid4().hex

    test_client.application.flow = Mock()
    test_client.application.flow.step2_exchange.return_value = Mock(
        id_token={'email': email}
    )

    monkeypatch.setattr(auth_views, 'build', lambda *args, **kwargs: Mock(**{
        'people.return_value': Mock(**{
            'get.return_value': Mock(**{
                'execute.return_value': {
                    'names': [{'displayName': uuid4().hex}]
                }
            })
        })
    }))

    return email


@pytest.mark.usefixtures('live_server')
class TestTheLoginProcess(object):

    def test_redirects_to_google(self):
        # This will only work online, since the view contacts Google to resolve
        # the redirect URL
        response = requests.get(
            url_for('auth.login', _external=True),
            allow_redirects=False
        )

        assert response.status_code == httplib.FOUND

        location = urlsplit(response.headers['location'])

        assert location.scheme == 'https'
        assert location.netloc.endswith('.google.com')
        assert 'auth' in location.path

        query = parse_qs(location.query)

        assert query['redirect_uri'][0] == url_for(
            'auth.oauth2callback',
            _external=True
        )
        assert query['response_type'][0] == 'code'
        assert query['scope'][0] == 'email profile'
        assert query['access_type'][0] == 'offline'
        assert 'client_id' in query
        assert 'state' in query

    def test_handles_responses_without_code_or_error(self, test_client):
        response = test_client.get(url_for('auth.oauth2callback'))
        assert response.status_code == httplib.BAD_REQUEST

    def test_handles_errors_without_a_code(self, test_client):
        error = 'Something is weird over here'

        response = test_client.get(url_for('auth.oauth2callback', error=error))

        assert error in response.data

    def test_requires_a_csrf_token(self, test_client, csrf_token):
        response = test_client.get(url_for('auth.oauth2callback', code='oauth_code'))

        assert response.status_code == httplib.UNAUTHORIZED
        assert 'Invalid CSRF token' in response.data

    def test_validates_the_csrf_token(self, test_client, csrf_token):
        response = test_client.get(
            url_for('auth.oauth2callback', code='oauth_code', state=csrf_token[:-1])
        )

        assert response.status_code == httplib.UNAUTHORIZED
        assert 'Invalid CSRF token' in response.data

    def test_handles_nonexistent_user(self, test_client, csrf_token, authenticated_email, monkeypatch):
        monkeypatch.setattr(auth_views.User, 'search', Mock(**{
            'return_value.filter.return_value.execute.return_value.hits.total': 0
        }))

        response = test_client.get(
            url_for('auth.oauth2callback', code='oauth_code', state=csrf_token)
        )

        assert response.status_code == httplib.UNAUTHORIZED
        assert 'no user with email address' in response.data

    def test_handles_ambiguous_user(self, test_client, csrf_token, authenticated_email, monkeypatch):
        @classmethod
        def get_by_email(cls, email):
            # Craft fake exception instead of triggering one in the original
            # `get_by_email` since `Response` objects are a pita to create/mock
            raise ConflictError('This is the ambiguous_user_test')
        monkeypatch.setattr(User, 'get_by_email', get_by_email)

        response = test_client.get(url_for('auth.oauth2callback', code='oauth_code', state=csrf_token))

        assert response.status_code == httplib.INTERNAL_SERVER_ERROR

    def test_can_return_jwt(self, test_client, csrf_token, authenticated_email, monkeypatch):
        jwt = uuid4().hex
        monkeypatch.setattr(auth_views, 'create_jwt', lambda name, user: jwt)

        @classmethod
        def get_by_email(cls, email):
            return User(username=uuid4().hex, email=authenticated_email, customers=[uuid4().hex])
        monkeypatch.setattr(User, 'get_by_email', get_by_email)

        response = test_client.get(url_for('auth.oauth2callback', code='oauth_code', state=csrf_token))

        assert response.status_code == httplib.OK
        assert response.mimetype == 'application/jwt'
        assert response.data == jwt

    def test_can_redirect_with_jwt(self, test_client, csrf_token, authenticated_email, monkeypatch):
        callback = 'https://example.com'

        jwt = uuid4().hex
        monkeypatch.setattr(auth_views, 'create_jwt', lambda name, user: jwt)

        @classmethod
        def get_by_email(cls, email):
            return User(username=uuid4().hex, email=authenticated_email, customers=[uuid4().hex])
        monkeypatch.setattr(User, 'get_by_email', get_by_email)

        with test_client.session_transaction() as session:
            session[auth_views.UrlParams.callback] = callback

        response = test_client.get(url_for('auth.oauth2callback', code='oauth_code', state=csrf_token))

        assert response.status_code == httplib.FOUND
        assert response.headers['Location'] == set_params(
            callback,
            {auth_views.UrlParams.token: jwt}
        )
