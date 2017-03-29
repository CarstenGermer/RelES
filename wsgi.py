# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from reles import create_app

application = create_app()

if __name__ == '__main__':
    application.run(port=8080)
