from __future__ import absolute_import

import click
import elasticsearch
from flask import current_app


@click.group()
def index():
    """Elasticsearch index management commands"""
    pass


@index.command()
@click.argument('index_name')
def create(index_name):
    """Create an index in elasticsearch"""
    click.secho('Creating index: %s...' % index_name, bold=True)

    # TODO get from context instead!
    es = current_app.es  # type: elasticsearch.Elasticsearch

    if es.indices.exists(index_name):
        click.secho('Index already exists!', fg='red')
    else:
        es.indices.create(index_name)
        click.secho('* Created.', fg='green')


@index.command()
def list():
    """List all indices in attached elasticsearch"""
    click.secho('Listing indexes:', bold=True)

    # TODO get from context instead!
    es = current_app.es  # type: elasticsearch.Elasticsearch

    indices = es.indices.get_aliases().keys()
    for index in sorted(indices):
        click.secho(index)
