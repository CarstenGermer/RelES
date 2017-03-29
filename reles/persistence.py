from __future__ import absolute_import

from collections import defaultdict

from elasticsearch import TransportError
from elasticsearch_dsl.connections import connections
from typing import Optional, Sequence  # noqa


def configure_elasticsearch(app):
    # type: (flask.app.Flask) -> elasticsearch.Elasticsearch

    # Setup connection
    es_host = app.config['ELASTICSEARCH_HOST']
    if es_host:
        app.es = connections.create_connection(hosts=[es_host])
    else:
        raise RuntimeError('No `ELASTICSEARCH_HOST` in RelES config')

    for index, doctypes in app.config['ELASTICSEARCH_MAPPINGS'].items():
        # Create index
        try:
            index.create()
        except TransportError as error:
            if 'already_exists' in error.error:
                app.logger.debug('Index `%s` exists', index._name)
            else:
                raise
        else:
            app.logger.info('Created index `%s`', index._name)

        # Initialize mappings
        for mapping in doctypes:
            app.logger.debug('Initializing doctype `%s`', mapping._doc_type.name)
            mapping.init(index=index._name)

    return app.es


class SwaggerSchemaStore(object):
    def __init__(self):
        # type: (None) -> None
        self._schemas = defaultdict(dict)

    def add_schema(self, endpoint, schema):
        # type: (str, dict) -> None
        self._schemas[endpoint]= schema

    def get_schema(self, endpoint, definition=None):
        # type: (str, str) -> dict
        return (
            self._schemas.get(endpoint) if not definition else
            self._schemas.get(endpoint, {}).get('definitions', {}).get(definition)
        )

    def list_definitions(self, endpoint):
        # type: (str) -> dict
        try:
            return self._schemas[endpoint]['definitions']
        except KeyError:
            return {}

    def list_endpoints(self):
        # type: () -> Sequence[str]
        return self._schemas.keys()


class DataStore(object):
    def __init__(self, es):
        # type: (elasticsearch.Elasticsearch) -> None
        self._es = es

    @staticmethod
    def _transform(es_document):
        result = {}
        result.update(es_document['_source'])
        result['_id'] = es_document['_id']

        # TODO is this actually an error in list()s result?
        if '_version' in es_document:
            result['_version'] = es_document['_version']

        return result

    def get_document(self, index, doc_type, id, version=None):
        # type: (str, str, str, int) -> dict
        document = self._es.get(index=index, doc_type=doc_type, id=id, refresh=True)
        return self._transform(document)

    def create_document(self, index, doc_type, document, id=None, refresh=False):
        # type: (str, str, dict, Optional[str]) -> dict
        created = self._es.index(
            index=index,
            doc_type=doc_type,
            body=document,
            id=id,
            refresh=refresh
        )

        return self.get_document(index, doc_type, created['_id'])

    def delete_document(self, index, doc_type, id):
        # type: (str, str, str) -> dict
        document = self.get_document(index, doc_type, id)

        self._es.delete(index=index, doc_type=doc_type, id=id)

        return document

    def list_documents(self, index, doc_type, limit=100, offset=0, refresh=False):
        # type: (str, str, int, int, boolean) -> Tuple[Sequence[dict], int]
        if refresh:
            self._es.indices.refresh(index=index)

        search_response = self._es.search(index=index, doc_type=doc_type, size=limit, from_=offset)
        hits = search_response['hits']

        return list(map(self._transform, hits.get('hits', []))), search_response['took']

    def update_document(self, index, doc_type, id, document, refresh=False):
        # type: (str, str, str, dict) -> dict

        # clean metadata
        document.pop('_id', None)
        _version = document.pop('_version', None)

        # wrap as partial doc update
        # (https://www.elastic.co/guide/en/elasticsearch/reference/current/docs-update.html)
        request = {
            'doc': document,
            'detect_noop': False,  # FIXME? we always write & increment version
        }

        update_args = {
            'index': index,
            'doc_type': doc_type,
            'id': id,
            'body': request,
            'refresh': refresh,
        }

        if _version:
            update_args['version'] = _version

        self._es.update(**update_args)

        return self.get_document(index, doc_type, id)

    def search_documents(self, index, doc_type, query, refresh=False):
        # type: (str, str, dict, boolean) -> Tuple[Sequence[dict], int]

        if refresh:
            self._es.indices.refresh(index=index)

        search_response = self._es.search(index=index, doc_type=doc_type, body={'query': query})
        hits = search_response['hits']

        return list(map(self._transform, hits.get('hits', []))), search_response['took']
