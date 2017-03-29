# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import time
from urllib import urlencode
from urlparse import parse_qs, urlparse, urlunparse

from flask import current_app as app
from flask import url_for
from jose import jwt
from oauth2client.client import flow_from_clientsecrets
from pathlib2 import Path

from .models import Customer


def create_oauth_flow():
    """Prepare Google OAuth workflow from config file."""
    app.flow = flow_from_clientsecrets(
        str(Path(app.config['ROOT_DIR'], 'configs/client_secrets.json')),
        scope=['email', 'profile'],
        redirect_uri=url_for('auth.oauth2callback', _external=True),
    )


def create_jwt(user, name=None, renewable=False):
    """Create a JWT."""
    session_user = sessionize_user(user, name)
    session_customer = sessionize_customer(
        Customer.get_by_name(user.customers[0])
    )

    return format_jwt(session_user, session_customer, renewable)


def sessionize_user(user, name):
    document = user.to_dict(include_meta=True)

    sessionized = {}
    sessionized.update(document['_source'])
    sessionized['_id'] = document['_id']
    sessionized['google_name'] = name

    return sessionized


def sessionize_customer(customer):
    document = customer.to_dict(include_meta=True)

    sessionized = {}
    sessionized.update(document['_source'])
    sessionized['_id'] = document['_id']

    return sessionized


def format_jwt(user, active_customer, renewable):
    """Format a JWT and MAC it."""
    now = int(time.time())

    claims = {
        # reserved: https://tools.ietf.org/html/rfc7519#section-4.1
        'exp': now + app.config['AUTH_TOKEN_LIFETIME'],
        'nbf': now,  # not before
        'iss': app.config['AUTH_TOKEN_ISSUER'],
        'iat': now,  # issue date
        # private: https://tools.ietf.org/html/rfc7519#section-4.3
        'user': user,
        'active_customer': active_customer,
        'renewable': renewable,
    }

    return jwt.encode(
        claims,
        key=app.config['AUTH_JWT_SECRET'],
        algorithm=app.config['AUTH_JWT_ALGORITHM'],
    )


def set_params(url, params):
    """Set GET parameters on a URL."""
    components = urlparse(url)

    query = parse_qs(components.query)
    query.update(params)

    components = components._replace(query=urlencode(query, doseq=True))
    return urlunparse(components)
