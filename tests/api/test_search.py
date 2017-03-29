# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals


import httplib

from flask import url_for
import pytest


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheSearchEndpoint(object):

    def test_charges_for_successful_queries(self, requests, customer):
        assert 'cycles' not in customer

        index = 'library'

        response = requests.post(
            url_for('document_search', index=index, doc_type='book', _external=True),
            json={
                'match_all': {}
            }
        )

        assert response.status_code == httplib.OK

        customer.refresh()

        # I failed to wrap anything on the `current_app` proxy in a `Mock`,
        # so this is the most we can assume
        assert customer.cycles['{}_{}_search'.format(index, customer.name)] > 0

    def test_does_not_charge_for_failed_requests(self, requests, customer):
        assert 'cycles' not in customer

        response = requests.post(
            url_for('document_search', index='library', doc_type='book', _external=True),
            json={
                'syntactically correct': {
                    'otherwise crap': {}
                }
            }
        )

        assert response.status_code == httplib.BAD_REQUEST

        customer.refresh()
        assert 'cycles' not in customer
