# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import elasticsearch_dsl as dsl
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.schema import CheckConstraint, Index, PrimaryKeyConstraint
from sqlalchemy.sql.functions import func

from .database import db


class VersioningException(Exception):
    pass


class DocumentVersion(db.Model):
    doc_type = db.Column(db.String, nullable=False)
    id = db.Column(db.String, nullable=False)
    version = db.Column(db.Integer, nullable=False, autoincrement=False)
    document = db.Column(JSON)

    def __init__(self, doc_type, pk, version, document):
        self.doc_type = doc_type
        self.id = pk
        self.version = version
        self.document = document

    __tablename__ = 'document_versions'
    __table_args__ = (
        PrimaryKeyConstraint('doc_type', 'id', 'version'),
        CheckConstraint(r"doc_type <> ''"),
        CheckConstraint(r"id <> ''"),
        CheckConstraint(r'version > 0'),

        # case insensitive unique constraint for our primary key
        Index('uniq_primary_ci', func.lower(doc_type), func.lower(id), version, unique=True),
    )


class ArchivingDocType(dsl.DocType):
    def __init__(self, meta=None, **kwargs):
        super(ArchivingDocType, self).__init__(meta, **kwargs)

    def save(self, using=None, index=None, validate=True, **kwargs):
        result = super(ArchivingDocType, self).save(using, index, validate,  **kwargs)

        archive_document_version(
            self._doc_type.name,
            self.meta.id,
            self.meta.version,
            self.to_dict(include_meta=True)
        )

        return result


def archive_document_version(doc_type, pk, version, document):
    # type: (str, str, int, dict) -> void

    # TODO route to different tables based on doc_type?
    document_version = DocumentVersion(
        doc_type,
        pk,
        version,
        document
    )

    try:
        db.session.add(document_version)
        db.session.commit()
    except (IntegrityError, StatementError) as e:
        db.session.rollback()
        raise VersioningException(e)
    else:
        return document_version


def retrieve_document_version(doc_type, pk, version):
    # type: (str, str, int) -> dict

    key_tuple = (doc_type, pk, version)

    document_version = DocumentVersion.query.get(key_tuple)

    if document_version:
        return document_version.document
    else:
        raise VersioningException('There is no version {} of {} \'{}\''.format(version, doc_type, pk))


def list_document_versions(doc_type, pk):
    # type: (str, str, int) -> Sequence[dict]

    document_versions = DocumentVersion.query.filter_by(doc_type=doc_type, id=pk).all()

    if document_versions:
        return [dv.document for dv in document_versions]
    else:
        raise VersioningException('There is no {} with ID \'{}\''.format(doc_type, pk))
