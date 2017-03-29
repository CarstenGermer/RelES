#!/usr/bin/env python
# coding: utf-8

"""An example for a Python client."""

from __future__ import absolute_import, print_function, unicode_literals

import httplib
from urlparse import urljoin
from uuid import uuid4
import sys

from requests import Session


RELES_URL = 'http://localhost:8080'


if __name__ == '__main__':
    # Just pass the file downloaded at the end of the login process as the
    # first argument to this script: `$ python client.py <token_file>`.
    jwt = open(sys.argv[1])

    client = Session()
    client.headers['Authorization'] = 'Bearer %s' % jwt.read()

    restaurants_url = urljoin(RELES_URL, '/restaurants/reles/')

    # Create a new restaurant
    response = client.post(restaurants_url, json={'name': uuid4().hex})
    if response.status_code == httplib.CREATED:
        print('Successfully created restaurant:', response.content)
    else:
        print('Failed to create restaurant:', response.content)

    # List all existing restaurants
    response = client.get(restaurants_url)
    print('All (indexed) restaurants:', response.content)
