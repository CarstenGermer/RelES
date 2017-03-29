from __future__ import print_function, unicode_literals

from datetime import datetime
from uuid import uuid4

from elasticsearch_dsl import Index
from elasticsearch_dsl.field import Date, Integer, String
import pytest

from reles.versioning import ArchivingDocType, retrieve_document_version


# inspired from https://github.com/elastic/elasticsearch-dsl-py#persistence-example
class ArchivingArticle(ArchivingDocType):
    title = String(analyzer='snowball', fields={'raw': String(index='not_analyzed')})
    body = String(analyzer='snowball')
    tags = String(index='not_analyzed')
    published_from = Date()
    lines = Integer()

    def save(self, **kwargs):
        self.lines = len(self.body.split())
        return super(ArchivingArticle, self).save(**kwargs)

    def is_published(self):
        return datetime.now() > self.published_from


@pytest.yield_fixture()
def blog_index():
    tmp_index = Index(uuid4().hex)
    tmp_index.create()

    yield tmp_index._name

    tmp_index.delete()


@pytest.yield_fixture(scope='function')
def article(db_session, blog_index):
    ArchivingArticle.init(index=blog_index)

    _id = uuid4().hex

    article = ArchivingArticle(meta={'id': _id}, title='Hello world!', tags=['test'])
    article.body = ''' looong text '''
    article.published_from = datetime.now()
    article.save(index=blog_index)

    yield ArchivingArticle.get(index=blog_index, id=_id)

    ArchivingArticle.get(index=blog_index, id=_id).delete()


@pytest.mark.usefixtures('db_session')
class TestArchival(object):
    def test_save_multiple(self, article):
        title1 = article.title
        version1 = article.meta.version

        article.title = ''.join(reversed(article.title))
        article.save()

        title2 = article.title
        version2 = article.meta.version

        assert title1 != title2
        assert version1 != version2

        archived1 = ArchivingArticle.from_es(
            retrieve_document_version(
                ArchivingArticle._doc_type.name,
                article.meta.id,
                version1
            )
        )

        archived2 = ArchivingArticle.from_es(
            retrieve_document_version(
                ArchivingArticle._doc_type.name,
                article.meta.id,
                version2
            )
        )

        assert archived1.title == title1
        assert archived1.meta.version == version1
        assert archived2.title == title2
        assert archived2.meta.version == version2

    def test_save_and_retrieve_archived(self, article):
        archived_document = retrieve_document_version(
            article.meta.doc_type,
            article.meta.id,
            article.meta.version
        )

        archived = ArchivingArticle.from_es(archived_document)

        assert archived == article

        # we don't expect 'found' in the archived document, strip it
        article.meta._d_.pop('found')

        # comparing _d_ so we get pretty "diff" from the assert on error
        assert archived.meta._d_ == article.meta._d_
