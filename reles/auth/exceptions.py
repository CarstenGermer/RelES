# coding: utf-8


from __future__ import absolute_import, print_function, unicode_literals


import httplib

from elasticsearch.exceptions import ConflictError, NotFoundError


class AuthError(Exception):
    pass


class NotFoundError(NotFoundError, AuthError):
    def __init__(self, error):
        super(NotFoundError, self).__init__(httplib.NOT_FOUND, error)


class ConflictError(ConflictError, AuthError):
    def __init__(self, error):
        super(ConflictError, self).__init__(httplib.CONFLICT, error)
