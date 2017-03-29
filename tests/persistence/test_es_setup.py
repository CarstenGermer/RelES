# coding: utf-8

from __future__ import absolute_import, unicode_literals

from uuid import uuid4

from elasticsearch import TransportError
from elasticsearch.client import ClusterClient
from elasticsearch_dsl import DocType, Index, Keyword
from elasticsearch_dsl.connections import connections
from flask import Flask
import pytest

from reles.default_config import ELASTICSEARCH_HOST
from reles.persistence import configure_elasticsearch


@pytest.fixture(scope='module')
def es():
    """Instantiate an ES client."""
    return connections.create_connection(hosts=[ELASTICSEARCH_HOST])


@pytest.yield_fixture()
def random_index():
    """Instantiate a random index."""
    index = Index(uuid4().hex)

    yield index

    if index.exists():
        index.delete()


@pytest.fixture()
def random_doctype():
    """Declare a random doctype."""
    class TestType(DocType):
        test_field = Keyword()
    return TestType


@pytest.fixture()
def app(es, random_index, random_doctype):
    """Create a minimalist test app."""
    app = Flask(__name__)
    app.config['ELASTICSEARCH_HOST'] = ELASTICSEARCH_HOST
    app.config['ELASTICSEARCH_MAPPINGS'] = {random_index: [random_doctype]}
    app.cluster = ClusterClient(es)

    return app


class TestTheEsSetup(object):

    def test_handles_an_incomplete_config(self, app):
        app.config['ELASTICSEARCH_HOST'] = None

        with pytest.raises(RuntimeError):
            configure_elasticsearch(app)

    def test_initializes_the_configured_mappings(self, es, random_index, random_doctype, app):
        assert random_index._name not in es.indices.get_alias()

        client = configure_elasticsearch(app)

        assert random_index._name in es.indices.get_alias()
        assert random_doctype._doc_type.name in es.indices.get_mapping()[random_index._name]['mappings']
        assert client == app.es

    def test_copes_with_an_existing_index(self, es, random_index, app):
        random_index.create()
        app.cluster.health(wait_for_status='yellow')

        configure_elasticsearch(app)
        assert random_index._name in es.indices.get_alias()

    def test_raises_unexpected_index_errors(self, random_index, app):
        random_index._name += '?'

        with pytest.raises(TransportError):
            configure_elasticsearch(app)
