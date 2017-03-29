from datetime import datetime
import logging

import pytest

from reles.versioning import (
    VersioningException,
    archive_document_version,
    list_document_versions,
    retrieve_document_version,
)

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)


@pytest.mark.usefixtures('db_session')
class TestWriteFailures(object):

    def test_doc_type_none_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version(None, 'valid_key', 1, {})

    def test_doc_type_empty_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('', 'valid_key', 1, {})

    def test_pk_none_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', None, 1, {})

    def test_pk_empty_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', '', 1, {})

    def test_version_none_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', 'valid_key', None, {})

    def test_version_zero_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', 'valid_key', 0, {})

    def test_version_lt_zero_fails(self):
        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', 'valid_key', -1, {})

    def test_duplicate_version_fails(self):
        archive_document_version('valid_doc_type', 'valid_key', 1, {'does_not': 'matter'})

        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', 'valid_key', 1, {'if_it': 'is_different'})

    def test_duplicate_different_case_doc_type_fails(self):
        archive_document_version('valid_doc_type', 'valid_key', 555, {'does_not': 'matter'})

        with pytest.raises(VersioningException):
            archive_document_version('VALID_doc_type', 'valid_key', 555, {'if_it': 'is_different'})

    def test_duplicate_different_case_id_fails(self):
        archive_document_version('valid_doc_type', 'valid_key', 666, {'does_not': 'matter'})

        with pytest.raises(VersioningException):
            archive_document_version('valid_doc_type', 'VALID_key', 666, {'if_it': 'is_different'})


@pytest.mark.usefixtures('db_session')
class TestReadWrite(object):

    def test_read_our_writes(self):
        expected = {'key1': 'value1'}
        archive_document_version('valid_doc_type', 'valid_key', 777, expected)
        actual = retrieve_document_version('valid_doc_type', 'valid_key', 777)

        assert actual == expected

    def test_read_missing(self):
        # make sure there is something in the db...
        archive_document_version('valid_doc_type', 'valid_key1', 888, {'key1': 'value1'})

        # but try to read something completely different
        with pytest.raises(VersioningException):
            retrieve_document_version('valid_doc_type', 'valid_key2', 888)

    def test_list_our_writes(self):
        expected = {'key1': 'value1'}
        archive_document_version('valid_doc_type', 'valid_key', 999, expected)
        all_archived = list_document_versions('valid_doc_type', 'valid_key')

        assert expected in all_archived


@pytest.mark.usefixtures('db_session')
class TestBugs(object):
    def test_datetime_gets_encoded(self):
        expected = {'key1': 'value1', 'when': datetime.now()}
        archive_document_version('valid_doc_type', 'valid_key', 2222, expected)

        actual = retrieve_document_version('valid_doc_type', 'valid_key', 2222)

        assert actual['when'] == expected['when'].isoformat()
