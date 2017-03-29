# coding: utf-8


"""
Blueprint for using google's oauth2 service to identify users.

This code may be extended to use openId later.
"""


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import hashlib
import httplib
from os import urandom

from apiclient.discovery import build
from enum import Enum
from flask import (
    Blueprint,
    abort,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    request,
    session,
)
import httplib2

from .exceptions import ConflictError, NotFoundError
from reles.views import error_response
from .models import Customer, User
from .utils import create_jwt, format_jwt, sessionize_customer, set_params

auth = Blueprint('auth', __name__)


state_error = Enum('state_error', ['not_in_request', 'not_in_session'])


class UrlParams(object):
    """URL parameter names for the login process."""

    callback = 'cb'
    token = 'auth'


@auth.route('/login', methods=['GET'])
def login():
    """Create a redirect to Google's login/consent page."""
    auth_uri = current_app.flow.step1_get_authorize_url()

    # Create a per-request state token to prevent CSRF
    # Store it in the session for later validation
    session['state'] = hashlib.sha256(urandom(1024)).hexdigest()
    auth_uri = set_params(auth_uri, {'state': session['state']})

    # Remember client callback
    if UrlParams.callback in request.args:
        session[UrlParams.callback] = request.args[UrlParams.callback]

    return redirect(auth_uri)


@auth.route('/renew_token', methods=['GET'])
def renew_token():
    """Extend a renewable token."""
    if g.token_is_renewable:
        try:
            # Check if user is still valid. If the token leaked, deleting the
            # compromised user is the only way to prevent indefinite renewals
            User.get_by_email(g.user['email'])
        except NotFoundError as error:
            return error_response(httplib.BAD_REQUEST, error.error)
        except ConflictError as error:
            current_app.logger.error(error.error)
            return error_response(
                httplib.INTERNAL_SERVER_ERROR,
                'failed to renew token'
            )

        new_token = format_jwt(
            g.user,
            sessionize_customer(Customer.get_by_name(g.customer['name'])),
            renewable=True,
        )
        response = make_response(new_token)
        response.headers['Content-Type'] = 'application/jwt'

        return response
    else:
        return error_response(httplib.BAD_REQUEST, 'token is not renewable')


@auth.route('/login/oauth2callback', methods=['GET'])
def oauth2callback():
    """
    Receive credentials from Google after user has given consent.

    Store credentials in session.
    """
    if 'code' not in request.args:
        abort(httplib.UNAUTHORIZED, request.args['error'])

    # Ensure that the request is not a forgery
    request_state = request.args.get('state', state_error.not_in_request)
    session_state = session.get('state', state_error.not_in_session)
    if request_state != session_state:
        abort(httplib.UNAUTHORIZED, 'Invalid CSRF token')

    # Exchange code for credentials
    credentials = current_app.flow.step2_exchange(request.args['code'])

    # Access user profile
    api = build('people', 'v1', http=credentials.authorize(httplib2.Http()))
    profile = api.people().get(resourceName='people/me').execute()
    name = profile['names'][0]['displayName']

    # Create a MACed JWT
    email = credentials.id_token['email']

    try:
        user = User.get_by_email(email)
    except NotFoundError as error:
        abort(httplib.UNAUTHORIZED, error.error)
    except ConflictError as error:
        current_app.logger.error(error.error)
        abort(httplib.INTERNAL_SERVER_ERROR)
    else:
        token = create_jwt(user, name)
        if UrlParams.callback in session:
            return redirect(
                set_params(
                    session[UrlParams.callback],
                    {UrlParams.token: token}
                )
            )
        else:
            response = make_response(token)
            response.headers['Content-Type'] = 'application/jwt'
            return response
    finally:
        session.clear()


@auth.route('/select_customer', methods=['GET'])
def activate_customer():

    new_customer = request.args.get('customer')

    if not new_customer:
        return error_response(
            httplib.BAD_REQUEST,
            'specify a customer to set as active'
        )

    if new_customer in g.user['customers']:
        token = format_jwt(
            g.user,
            sessionize_customer(Customer.get_by_name(new_customer)),
            g.token_is_renewable,
        )
        response = make_response(token)
        response.headers['Content-Type'] = 'application/jwt'
        return response
    else:
        return error_response(httplib.BAD_REQUEST, 'invalid customer')
