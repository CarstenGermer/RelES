from __future__ import absolute_import

from datetime import datetime, timedelta

import click
from flask import current_app
from pathlib2 import Path


@click.group()
def files():
    """File management commands"""
    pass


@files.command()
def cleanse():
    """Remove old unreferenced media files."""

    now = datetime.now()
    max_age = timedelta(minutes=7)

    p = Path(current_app.config['UPLOAD_MNT'])

    click.echo('Looking for unreferenced uploaded files...')
    for child in p.rglob('*'):
        if not child.is_file():
            continue

        public_path = str(child.relative_to(p))

        mtime = datetime.fromtimestamp(
            child.stat().st_mtime
        )

        if now - mtime < max_age:
            click.secho('* %s is fresh, skipping' % child, fg='green')
        else:
            media_documents, _ = current_app.datastore.search_documents(
                index='media',
                doc_type=None,
                query={'term': {'sys_filename.raw': public_path}}
            )

            if len(media_documents) > 0:
                click.secho('* %s is in use, skipping' % child, fg='green')
            else:
                click.secho('* %s is stale and unreferenced, deleting' % child, fg='yellow')
                child.unlink()

    click.echo('Removing any empty directories...')
    for child in p.rglob('*'):
        if not child.is_dir():
            continue

        try:
            child.rmdir()
        except OSError:
            # expected for all nonempty dirs, faster than checking if they are indeed empty
            pass
        else:
            click.secho('* deleted: %s' % child, fg='yellow')

    click.echo('Done.')
