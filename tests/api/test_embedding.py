# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

import httplib

from flask import url_for
import pytest


@pytest.mark.usefixtures('live_server', 'customer_with_library_permissions')
class TestTheGetEndpoint(object):

    def test_can_embed_a_single_top_level_document(self, requests, book, author):
        assert book['author'] == author['_id']

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='book',
                id=book['_id']
            ),
            params={'embed': 'author'},
        )

        assert response.status_code == httplib.OK

        assert response.json()['author'] == author

    def test_can_embed_a_list_of_top_level_documents(self, requests, book_series, book, another_book):
        assert book_series['books'] == [book['_id'], another_book['_id']]

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='series',
                id=book_series['_id'],
            ),
            params={'embed': 'books'}
        )

        assert response.status_code == httplib.OK

        assert response.json()['books'] == [book, another_book]

    def test_can_embed_nested_documents(self, requests, book_series, book, another_book, author):
        assert book_series['books'] == [book['_id'], another_book['_id']]
        # Note: both books have the same author. It's a series, after all ;)
        assert book['author'] == author['_id']
        assert another_book['author'] == author['_id']

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='series',
                id=book_series['_id'],
            ),
            params={'embed': ['books', 'books.author']}
        )

        assert response.status_code == httplib.OK

        series = response.json()

        assert series['books'][0]['title'] == book['title']
        assert series['books'][0]['author'] == author

        assert series['books'][1]['title'] == another_book['title']
        assert series['books'][1]['author'] == author

    def test_can_embed_lists_of_nested_documents(self, requests, book, author, book_award, another_book_award):
        assert book['author'] == author['_id']
        assert author['awards'] == [book_award['_id'], another_book_award['_id']]

        response = requests.get(
            url_for(
                'document_retrieve',
                index='library',
                doc_type='book',
                id=book['_id'],
            ),
            params={'embed': ['author', 'author.awards']}
        )

        assert response.status_code == httplib.OK

        author_ = response.json()['author']

        assert author_['name'] == author['name']
        assert author_['awards'][0]['title'] == book_award['title']
        assert author_['awards'][1]['title'] == another_book_award['title']
