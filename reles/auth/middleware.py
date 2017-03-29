# coding: utf-8


"""Middleware using JWT access header to fetch authenticated user."""


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import httplib
import os

from flask import current_app, g
from flask import request as current_request
from jose import ExpiredSignatureError, JWTError, jwt

from .exceptions import AuthError
from ..views import error_response


def login_required():
    endpoint = current_request.path.split(os.sep)[1]

    spec = current_app.schemastore.get_schema(endpoint)
    if spec is None:
        current_app.logger.debug(
            'There is no spec for endpoint \'%s\' (parsed from \'%s\')',
            endpoint,
            current_request.path,
        )
        raise AuthError('Failed to determine security requirements')
    else:
        # This would need to get smarter if we wanted more specific security
        # settings further down the tree. A swagger parser would be nice to
        # match `paths` against the request, since the spec may contain
        # `parameters` `"in": "path"`.
        security_requirements = spec.get('security', {})

    return 'jwt' in [
        name for requirement in security_requirements
        for name in requirement.keys()
    ]


def authenticate_user():
    """Resolve JWT into `User` instance."""
    try:
        if not login_required():
            return
    except AuthError as error:
        return error_response(httplib.UNAUTHORIZED, error.message)

    auth_header = current_request.headers.get('Authorization', '').split()

    if len(auth_header) != 2 or auth_header[0] != 'Bearer':
        return error_response(httplib.UNAUTHORIZED, 'Authentication failed')

    try:
        claims = jwt.decode(
            auth_header[1],
            key=current_app.config['AUTH_JWT_SECRET'],
            algorithms=current_app.config['AUTH_JWT_ALGORITHM']
        )
    except ExpiredSignatureError as error:
        # This is a specialized `JWTError`, so check first
        return error_response(httplib.UNAUTHORIZED, 'Your token has expired')
    except JWTError as error:
        current_app.logger.debug(
            'Failed to decode JWT \'%s\': %s',
            auth_header[1],
            error.message,
        )
        return error_response(httplib.UNAUTHORIZED, 'Authentication failed')
    else:
        g.user = claims['user']
        g.customer = claims['active_customer']
        g.token_is_renewable = claims['renewable']
