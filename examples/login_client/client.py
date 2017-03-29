#!/usr/bin/env python
# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from flask import Flask, session, redirect, request, url_for
from jose import jwt
import json


app = Flask(__name__)
app.config['SERVER_NAME'] = 'localhost:8081'
app.config['RELES_HOST'] = 'localhost:8080'
app.config['SECRET_KEY'] = '3956f554cf08403b9a5e705a4612a048'


@app.route('/')
def index():
    if not 'jwt' in session:
        return redirect(url_for('login'))

    return 'Welcome %s' % json.loads(
        jwt.get_unverified_claims(session['jwt'])
    )['google_name']


@app.route('/login')
def login():
    # No HTTPS? ORLY?!
    return 'Please <a href="http://%s/login?cb=%s">log into the RelES</a>.' % (
        app.config['RELES_HOST'],
        url_for('token', _external=True)
    )


@app.route('/token')
def token():
    session['jwt'] = request.args['auth']
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
