from uuid import uuid4

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
import pytest

from reles.persistence import DataStore


@pytest.fixture()
def datastore(app):
    return DataStore(app.es)


@pytest.yield_fixture(scope='module')
def test_index(app):
    index_name = uuid4().hex

    Index(index_name).create()
    app.cluster.health(wait_for_status='yellow')

    yield index_name

    Index(index_name).delete()


@pytest.fixture()
def random_doctype(test_index, app):
    doc_type =  uuid4().hex

    app.es.indices.put_mapping(
        index=test_index,
        doc_type=doc_type,
        body={'dynamic': True}
    )

    return doc_type


class TestPersistenceDataStore(object):
    def test_list_empty(self, datastore, test_index, random_doctype):
        assert datastore.list_documents(test_index, random_doctype)[0] == []

    def test_create(self, datastore, test_index, random_doctype):
        document = {'key1': 'value1'}

        created = datastore.create_document(test_index, random_doctype, document)

        assert 'key1' in created

    def test_create_and_list(self, datastore, test_index, random_doctype):
        document = {'key1': 'value1'}

        created = datastore.create_document(test_index, random_doctype, document)

        assert 'key1' in created

        # ideally we would add a test that checks for failure without refresh(), but it's a race...
        Index(test_index).refresh()

        documents, _ = datastore.list_documents(test_index, random_doctype)

        assert len(documents) == 1
        assert 'key1' in documents[0]

    def test_create_and_get(self, datastore, test_index, random_doctype):
        document = {'key1': 'value1'}

        created = datastore.create_document(test_index, random_doctype, document)

        assert 'key1' in created

        retrieved = datastore.get_document(test_index, random_doctype, created['_id'])

        assert created == retrieved

    def test_create_and_update(self, datastore, test_index, random_doctype):
        document_v1 = {'key1': 'value1', 'key2': 'value2'}
        document_v2 = {'key2': 'value2updated', 'key3': 'value3added'}

        created = datastore.create_document(test_index, random_doctype, document_v1)

        assert 'key1' in created

        updated = datastore.update_document(test_index, random_doctype, created['_id'], document_v2)

        assert 'key1' in updated
        assert updated['key1'] == document_v1['key1']
        assert 'key2' in created
        assert updated['key2'] == document_v2['key2']
        assert 'key3' in updated
        assert updated['key3'] == document_v2['key3']

        assert updated['_version'] > created['_version']

    def test_does_not_create_without_authorization(self, datastore, random_doctype):
        with pytest.raises(NotFoundError):
            datastore.create_document('nosuch_aliasor_index', random_doctype, {})

    def test_does_not_list_without_authorization(self, datastore, random_doctype):
        with pytest.raises(NotFoundError):
            datastore.list_documents('nosuch_aliasor_index', random_doctype)

    def test_does_not_get_without_authorization(self, datastore, random_doctype):
        with pytest.raises(NotFoundError):
            datastore.get_document('nosuch_aliasor_index', random_doctype, 'random_id')

    def test_does_not_update_without_authorization(self, datastore, random_doctype):
        with pytest.raises(NotFoundError):
            datastore.update_document('nosuch_aliasor_index', random_doctype, 'random_id', {'new': 'document'})
