# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals


import httplib
from uuid import uuid4

from flask import url_for
import pytest

from reles.auth.aliases import  get_alias, AliasType


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheCreateEndpoint(object):

    def test_charges_successful_requests(self, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.write.name)

        response = requests.post(
            url_for(
                'document_create',
                index=index,
                doc_type='book',
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.CREATED

        customer.refresh()
        assert customer.cycles[alias] == app.config['CYCLES_CRUD']

    def test_does_not_charge_if_validation_fails(self, requests, customer):
        assert 'cycles' not in customer

        invalid_book = {'subtitle': 'A book needs a title!'}

        response = requests.post(
            url_for(
                'document_create',
                index='library',
                doc_type='book',
            ),
            json=invalid_book,
        )

        assert response.status_code == httplib.BAD_REQUEST

        customer.refresh()
        assert 'cycles' not in customer


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheRetrieveEndpoint(object):

    def test_charges_successful_requests(self, book, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.read.name)

        response = requests.get(
            url_for(
                'document_retrieve',
                index=index,
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.OK

        customer.refresh()
        assert customer.cycles[alias] == app.config['CYCLES_CRUD']

    def test_does_not_charge_failed_requests(self, requests, customer):
        assert 'cycles' not in customer

        invalid_id = 'does not exist'

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='book',
                id=invalid_id,
            )
        )

        assert response.status_code == httplib.NOT_FOUND

        customer.refresh()
        assert 'cycles' not in customer


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheUpdateEndpoint(object):

    def test_charges_on_successful_updates(self, book, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.write.name)

        response = requests.put(
            url_for(
                'document_update',
                index=index,
                doc_type='book',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex
            }
        )

        assert response.status_code == httplib.OK

        customer.refresh()
        assert customer.cycles[alias] == app.config['CYCLES_CRUD']

    def test_does_not_charge_if_validation_fails(self, book, requests, customer, app):
        assert 'cycles' not in customer

        invalid_title = ''

        response = requests.put(
            url_for(
                'document_update',
                index='library',
                doc_type='book',
                id=book['_id']
            ),
            json={
                'title': invalid_title
            }
        )

        assert response.status_code == httplib.BAD_REQUEST

        customer.refresh()
        assert 'cycles' not in customer


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheDeleteEndpoint(object):

    def test_charges_on_successful_delete(self, book, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.write.name)

        response = requests.delete(
            url_for(
                'document_delete',
                index=index,
                doc_type='book',
                id=book['_id'],
            ),
        )

        assert response.status_code == httplib.OK

        customer.refresh()
        assert customer.cycles[alias] == app.config['CYCLES_CRUD']

    def test_charges_on_invalid_id(self, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.write.name)

        invalid_id = 'does not exist'

        response = requests.delete(
            url_for(
                'document_delete',
                index=index,
                doc_type='book',
                id=invalid_id,
            ),
        )

        assert response.status_code == httplib.NOT_FOUND

        customer.refresh()
        assert customer.cycles[alias] == app.config['CYCLES_CRUD']


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheListEndpoint(object):

    def test_charges_on_success(self, requests, customer):
        assert 'cycles' not in customer

        index = 'library'
        alias = get_alias(index, customer.name, AliasType.read.name)

        response = requests.get(
            url_for(
                'document_list',
                index=index,
                doc_type='book',
            ),
        )

        assert response.status_code == httplib.OK

        customer.refresh()

        # I failed to wrap anything on the `current_app` proxy in a `Mock`,
        # so this is the most we can assume
        assert customer.cycles[alias] > 0

    def test_does_not_charge_on_failure(self, requests, customer, app):
        assert 'cycles' not in customer

        index = 'library'

        # provoke an error
        app.es.indices.delete(index)

        response = requests.get(
            url_for(
                'document_list',
                index=index,
                doc_type='book',
            ),
        )

        assert response.status_code == httplib.INTERNAL_SERVER_ERROR
        assert 'index not found' in response.json()['message']

        customer.refresh()
        assert 'cycles' not in customer
