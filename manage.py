#!/usr/bin/env python

from __future__ import absolute_import

import logging

import click

from scripts.auth import customers, permissions, users
from scripts.files import files
from scripts.persistence import index
from scripts.util import shell, runserver
from scripts.categories import categories


@click.group()
def cli():
    pass

cli.add_command(customers)
cli.add_command(files)
cli.add_command(index)
cli.add_command(permissions)
cli.add_command(runserver)
cli.add_command(shell)
cli.add_command(users)
cli.add_command(categories)

logging.basicConfig(level=logging.WARNING)

if __name__ == '__main__':
    from reles import create_app
    app = create_app()
    with app.app_context():
        cli()
