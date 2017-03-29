# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals


import httplib
from uuid import uuid4

from flask import url_for
import pytest


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestBlockedRiskyESEndpoints(object):

    def test_post_updatebyquery_type(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='library',
                doc_type='_update_by_query'
            ),
            json={
                'title': uuid4().hex,
            }
        )
        assert response.status_code == httplib.BAD_REQUEST
        assert '_update_by_query' in response.json()['message']

    def test_post_updatebyquery_index(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='_update_by_query',
                doc_type='book'
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_put_updatebyquery_type(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='library',
                doc_type='_update_by_query',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert '_update_by_query' in response.json()['message']

    def test_put_updatebyquery_index(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='_update_by_query',
                doc_type='book',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_get_updatebyquery_type(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='_update_by_query',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_get_updatebyquery_index(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='_update_by_query',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_delete_updatebyquery_type(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='library',
                doc_type='_update_by_query',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_delete_updatebyquery_index(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='_update_by_query',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_post_tasks_type(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='library',
                doc_type='_tasks'
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert '_tasks' in response.json()['message']

    def test_post_tasks_index(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='_tasks',
                doc_type='book'
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_put_tasks_type(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='library',
                doc_type='_tasks',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert '_tasks' in response.json()['message']

    def test_put_tasks_index(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='_tasks',
                doc_type='book',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_get_tasks_type(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='_tasks',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_get_tasks_index(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='_tasks',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_delete_tasks_type(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='library',
                doc_type='_tasks',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_delete_tasks_index(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='_tasks',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_post_reindex_type(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='library',
                doc_type='_reindex'
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert '_reindex' in response.json()['message']

    def test_post_reindex_index(self, requests):

        response = requests.post(
            url_for(
                'document_create',
                index='_reindex',
                doc_type='book'
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_put_reindex_type(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='library',
                doc_type='_reindex',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.BAD_REQUEST
        assert '_reindex' in response.json()['message']

    def test_put_reindex_index(self, book, requests):

        response = requests.put(
            url_for(
                'document_update',
                index='_reindex',
                doc_type='book',
                id=book['_id']
            ),
            json={
                'title': uuid4().hex,
            }
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_get_reindex_type(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='_reindex',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_get_reindex_index(self, book, requests):

        response = requests.get(
            url_for(
                'document_retrieve',
                index='_reindex',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED

    def test_delete_reindex_type(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='library',
                doc_type='_reindex',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.NOT_FOUND
        assert 'document not found' in response.json()['message']

    def test_delete_reindex_index(self, book, requests):

        response = requests.delete(
            url_for(
                'document_delete',
                index='_reindex',
                doc_type='book',
                id=book['_id']
            )
        )

        assert response.status_code == httplib.UNAUTHORIZED
