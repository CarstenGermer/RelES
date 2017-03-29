# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from uuid import uuid4

import pytest

from reles.persistence import DataStore


@pytest.fixture
def datastore(app):
    return DataStore(app.es)


@pytest.yield_fixture
def test_index(app):
    index_name = uuid4().hex
    app.es.indices.create(index_name)
    app.cluster.health(wait_for_status='yellow')

    yield index_name

    app.es.indices.delete(index_name)


@pytest.fixture
def test_doc_type(test_index, app):
    doc_type =  uuid4().hex

    app.es.indices.put_mapping(
        index=test_index,
        doc_type=doc_type,
        body={'properties': {'key1': {'type': 'string'}}}
    )

    return doc_type


@pytest.fixture
def random_id():
    return uuid4().hex
