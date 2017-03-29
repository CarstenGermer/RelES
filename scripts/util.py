from __future__ import absolute_import

try:
    from IPython import start_ipython
    from traitlets.config.loader import Config

    class InteractiveConsole(object):
        def __init__(self, locals):
            self._locals = locals

        def interact(self, banner):
            start_ipython(
                argv=[],
                user_ns=self._locals,
                config=Config(TerminalInteractiveShell={'banner2': banner})
            )
except ImportError:
    from code import InteractiveConsole

import click
from flask import current_app


_BANNER = """
  ,ad8888ba,    ,ad8888ba,   ,ad8888ba,  88888888ba,   888b      88
 d8"'    `"8b  d8"'    `"8b d8"'    `"8b 88      `"8b  8888b     88
d8'           d8'          d8'           88        `8b 88 `8b    88
88            88           88            88         88 88  `8b   88
88      88888 88           88            88         88 88   `8b  88
Y8,        88 Y8,          Y8,           88         8P 88    `8b 88
 Y8a.    .a88  Y8a.    .a8P Y8a.    .a8P 88      .a8P  88     `8888
  `"Y88888P"    `"Y8888Y"'   `"Y8888Y"'  88888888Y"'   88      `888

Welcome! Checkout the available context variables:
    {}
"""


@click.command()
def shell():
    """Runs a Python shell inside Flask application context."""
    context = {
        'app': current_app,
        'es': current_app.es,
    }

    banner = _BANNER.format('\n    '.join(context.keys()))

    InteractiveConsole(locals=context).interact(banner=banner)


@click.command()
@click.option('--port', '-p', type=int, help='Override PORT setting.')
@click.option('--debug/--no-debug', '-d/-D', default=None, help='Override DEBUG setting.')
def runserver(port, debug):
    """Runs the Flask development server i.e. app.run()."""
    if debug is not None:
        current_app.debug = debug

    if not port:
        port = current_app.config['PORT']

    click.echo('* Running on http://127.0.0.1:%s/ (Press CTRL+C to quit)' % port)
    current_app.run(port=port)
