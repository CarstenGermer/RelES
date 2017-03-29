# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from jsonschema import Draft4Validator, SchemaError, ValidationError
import pytest


def validate(schema, instance):
    try:
        Draft4Validator(schema).validate(instance)
    except ValidationError as e:
        pytest.fail(
            'Data does not match schema, should only happen while developing'
            ' tests! %s' % e
        )
    else:
        return instance


def check_schema(schema):
    try:
        Draft4Validator.check_schema(schema)
    except SchemaError as e:
        pytest.fail(
            'invalid schema in test, should only happen while developing'
            ' tests! %s' % e
        )
    else:
        return schema
