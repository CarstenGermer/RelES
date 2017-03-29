from __future__ import absolute_import

import click

from reles import create_app


@click.command()
@click.option('--port', default=9999, help='Port to listen on (default: 9999)')
def cli(port):
    create_app('schemas').run(port=port)

if __name__ == '__main__':
    cli()
