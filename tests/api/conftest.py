from __future__ import absolute_import, print_function, unicode_literals

from contextlib import contextmanager
from uuid import uuid4

from elasticsearch import NotFoundError
import pytest

from reles import configure_index, configure_mappings
from reles.auth.aliases import AliasType


@pytest.yield_fixture
def customer_with_library_permissions(auth_index, customer, app):
    with authorized_customer('library', auth_index, customer, app) as c:
        yield c


@pytest.yield_fixture
def customer_with_media_permissions(auth_index, customer, app):
    with authorized_customer('media', auth_index, customer, app) as c:
        yield c


@contextmanager
def authorized_customer(target_index, auth_index, customer, app):
    if not app.es.indices.exists(target_index):
        schema = app.schemastore.get_schema(target_index)
        configure_index(
            target_index,
            schema,
            app.config['ELASTICSEARCH_NON_RESETTABLE_INDEX_SETTINGS'],
            app.es
        )
        configure_mappings(
            target_index,
            schema,
            app.es,
        )

    customer.add_permissions(
        {target_index: [AliasType.read.name, AliasType.write.name]}
    )
    customer.save(index=auth_index._name, refresh=True)

    yield customer

    # update reference
    customer.refresh()
    customer.remove_permissions(
        {target_index: [AliasType.read.name, AliasType.write.name]}
    )
    customer.save(index=auth_index._name, refresh=True)

    try:
        app.es.indices.delete(target_index)
    except NotFoundError:
        # We don't mind as long as it's gone
        pass


@pytest.yield_fixture
def book_award(app):
    award = app.datastore.create_document(
        index='library',
        doc_type='award',
        document={'title': uuid4().hex},
        refresh=True,
    )

    yield award

    try:
        app.datastore.delete_document(
            index='library',
            doc_type='award',
            id=award['_id'],
        )
    except NotFoundError:
        # We don't mind as long as it's gone
        pass


another_book_award = book_award


@pytest.yield_fixture
def author(book_award, another_book_award, app):
    author = app.datastore.create_document(
        index='library',
        doc_type='author',
        document={
            'name': uuid4().hex,
            'awards': [book_award['_id'], another_book_award['_id']]
        },
        refresh=True,
    )

    yield author

    try:
        app.datastore.delete_document(
            index='library',
            doc_type='author',
            id=author['_id'],
        )
    except NotFoundError:
        # We don't mind as long as it's gone
        pass


@pytest.yield_fixture
def book(author, app):
    book = app.datastore.create_document(
        index='library',
        doc_type='book',
        document={
            'author': author['_id'],
            'title': uuid4().hex,
        },
        refresh=True,
    )

    yield book

    try:
        app.datastore.delete_document(
            index='library',
            doc_type='book',
            id=book['_id'],
        )
    except NotFoundError:
        # We don't mind as long as it's gone
        pass


another_book = book

@pytest.yield_fixture
def book_series(book, another_book, app):
    series = app.datastore.create_document(
        index='library',
        doc_type='series',
        document={
            'title': uuid4().hex,
            'books': [book['_id'], another_book['_id']]
        },
        refresh=True,
    )

    yield series

    try:
        app.datastore.delete_document(
            index='library',
            doc_type='book',
            id=series['_id'],
        )
    except NotFoundError:
        # We don't mind as long as it's gone
        pass
