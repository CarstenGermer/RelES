# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import httplib
from uuid import uuid4

from flask import url_for
import pytest


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheArchiveEndpoint(object):

    def test_retrieve_archived_matches_created(self, requests):
        book = {
            'title': 'Das Kapital',
        }

        created = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json=book,
            allow_redirects=False
        ).json()

        assert 'title' in created
        assert book['title'] == created['title']

        assert '_id' in created
        assert '_version' in created

        doc_id = created['_id']
        doc_version = created['_version']

        from_archive = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=doc_id,
                version=doc_version,
                _external=True
            ),
            allow_redirects=False
        ).json()

        assert from_archive == [created]

    def test_retrieve_archived_is_listed(self, requests):
        book = {
            'title': 'Das Kapital',
        }

        created = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json=book,
            allow_redirects=False
        ).json()

        assert '_id' in created
        doc_id = created['_id']

        all_archived = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=doc_id,
                _external=True
            ),
            allow_redirects=False
        ).json()

        assert len(all_archived) == 1
        assert all_archived[0] == created

    def test_retrieve_updated_is_archived(self, requests):
        book = {
            'title': 'Das Kapital',
        }

        created = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json=book,
            allow_redirects=False
        ).json()

        assert '_version' in created
        assert '_id' in created
        doc_id = created['_id']

        book2 = created.copy()
        book2['title'] = 'Das Kapital 2'

        updated = requests.put(
            url_for('document_update', index='library', doc_type='book', id=doc_id, _external=True),
            json=book2,
            allow_redirects=False
        ).json()

        assert '_version' in updated
        assert updated['_version'] > created['_version']

        all_archived = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=doc_id,
                _external=True
            ),
            allow_redirects=False
        ).json()

        assert len(all_archived) == 2
        assert created in all_archived
        assert updated in all_archived

    def test_can_retrieve_multiple_versions(self, requests):
        # Setup
        original = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        updated_1 = requests.put(
            url_for('document_update', index='library', doc_type='book', id=original['_id'], _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        updated_2 = requests.put(
            url_for('document_update', index='library', doc_type='book', id=original['_id'], _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        # Test
        versions = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=original['_id'],
                version=[original['_version'], updated_2['_version']],
                _external=True
            ),
            allow_redirects=False
        ).json()

        # Check
        assert len(versions) == 2
        assert original in versions
        assert updated_2 in versions

    def test_ignores_invalid_version_values(self, requests):
        # Setup
        original = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        updated_1 = requests.put(
            url_for('document_update', index='library', doc_type='book', id=original['_id'], _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        updated_2 = requests.put(
            url_for('document_update', index='library', doc_type='book', id=original['_id'], _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        # Test
        versions = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=original['_id'],
                version=['a', True, updated_1['_version'], 1.4142],
                _external=True
            ),
            allow_redirects=False
        ).json()

        # Check
        assert versions == [updated_1]

    def test_handles_nonexistent_versions(self, requests):
        # Setup
        original = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        # Test
        nonexistent_version = original['_version'] + 1
        error = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=original['_id'],
                version=nonexistent_version,
                _external=True
            ),
            allow_redirects=False
        ).json()

        # Check
        assert isinstance(error, dict)
        assert 'message' in error
        assert 'version' in error['message']
        assert str(nonexistent_version) in error['message']
        assert 'no version {}'.format(nonexistent_version) in error['message']

    def test_handles_empty_version_values(self, requests):
        # Setup
        original = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json={'title': uuid4().hex},
            allow_redirects=False
        ).json()

        # Test
        versions = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=original['_id'],
                version='',
                _external=True
            ),
            allow_redirects=False
        ).json()

        # Check
        #  If no (valid) versions are specified, all versions are listed
        assert versions == [original]

    def test_charges_per_version(self, requests, customer, app):
        assert 'cycles' not in customer

        # Setup
        versions = [
            {'title': 'The Goodfather'},
            {'title': 'The Godfather'},
        ]

        document = requests.post(
            url_for('document_create', index='library', doc_type='book', _external=True),
            json=versions[0],
            allow_redirects=False
        ).json()

        requests.put(
            url_for('document_update', index='library', doc_type='book', id=document['_id'], _external=True),
            json=versions[1],
            allow_redirects=False
        )

        # Test
        requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=document['_id'],
                _external=True
            ),
            allow_redirects=False
        )

        # Check
        customer.refresh()
        assert customer.cycles['_get_archived_book'] == len(versions) * app.config['CYCLES_GET_ARCHIVED_DOCUMENT']

    def test_charges_only_successful_requests(self, requests, customer):
        assert 'cycles' not in customer

        nonexistent_id = 'DoesNotExist'

        # Test
        #  without version
        response = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=nonexistent_id,
                _external=True
            ),
            allow_redirects=False
        )

        assert response.status_code == httplib.NOT_FOUND

        # Check
        customer.refresh()
        assert 'cycles' not in customer

        # Test
        #  with version
        response = requests.get(
            url_for(
                'document_retrieve_archived',
                index='library',
                doc_type='book',
                id=nonexistent_id,
                version=5,
                _external=True
            ),
            allow_redirects=False
        )

        assert response.status_code == httplib.NOT_FOUND

        # Check
        customer.refresh()
        assert 'cycles' not in customer
