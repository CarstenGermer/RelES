# coding: utf-8


"""Command for filling the categories."""


from __future__ import absolute_import


from functools import partial
import httplib

import click
from elasticsearch_dsl import Q
from flask import current_app as app
from jsonschema import ValidationError
import unicodecsv as csv

from reles.views import _processor, _validator


index = 'categories'
csv_field_names = [
    'type',
    'category_de',
    'category_en',
    'parent',
    'code'
]


@click.group()
def categories():
    """Categories management commands"""


@categories.command(name='import')
@click.argument('csv_file', type=click.File('rb'))
def import_csv(csv_file):
    """Import catgories from CSV/TSV file"""
    click.secho('Importing categories from %s' % csv_file.name, bold=True)

    RememberID = ''

    reader = csv.DictReader(
        csv_file,
        csv_field_names,
        delimiter=',',
    )

    for row in reader:
        click.secho(
            'Indexing category {} {} {}'.format(
                row['type'],
                row['category_de'].encode('utf-8'),
                row['parent'],
                row['code'].encode('utf-8')
            ),
            fg='green',
        )

        validator = _validator(index, row['type'])
        processor = _processor(index, row['type'])

        if (row['parent'] == "<"):
            # Remember IF of created Document after creation
            RememberID = 'yes'
            row['parent'] = '!'

        if (row['parent'] == '>'):
            # Set the currently remembered ID as parent
            row['parent'] = RememberID

        # if row['code'] is used as ID on creation, if not empty
        docID = row['code']

        # If parent is set to '!' (not) don't create the field 'entry_parent' in the new document
        if (row['parent'] == '!'):
            NewDoc = _create_document(
                row['type'],
                {
                    'de': [row['category_de']],
                    'en': [row['category_en']],
                    'code': row['code']
                },
                validator,
                processor,
                docID
            )
        else:
            NewDoc = _create_document(
                row['type'],
                {
                    'entry_parent': row['parent'],
                    'de': [row['category_de']],
                    'en': [row['category_en']],
                    'code': row['code']
                },
                validator,
                processor,
                docID
            )

        if (RememberID == 'yes'):
            # remember the ID of the created document
            RememberID = NewDoc['_id']

def _create_document(doc_type, data, validator, processor, docid):
    # validate
    try:
        validator.validate(data)
    except ValidationError as e:
        click.secho(
            'Failed to create {}: {}'.format(
                doc_type,
                e.message
            ),
            fg='red'
        )
        raise click.Abort()

    # augment
    document = processor.process(data)

    # create
    if (docid != ''):
        return app.datastore.create_document(index, doc_type, document, id=docid, refresh=True)
    else:
        return app.datastore.create_document(index, doc_type, document, refresh=True)
