from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from collections import Iterable
from functools import reduce
import operator

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Q
from flask import current_app as app
from geopy.distance import Point, distance
from jsonschema import ValidationError
from jsonschema.validators import Draft4Validator, extend
from pathlib2 import Path


def _required(validator, ref, instance, schema):
    for field in ref:
        if field not in instance:
            yield ValidationError(
                'field \'{}\' is required'.format(field)
            )
        elif isinstance(instance[field], Iterable) and not instance[field]:
            # reject '', [] and {} but allow 0
            yield ValidationError(
                'field \'{}\' must not be empty'.format(field)
            )


def _fkey(validator, ref, instance, schema):
    index = ref['index']
    doc_type = ref['doc_type']

    try:
        validator.datastore.get_document(index, doc_type, instance)
    except NotFoundError:
        yield ValidationError(
            'Invalid foreign key: no such document {}/{}/{}'.format(
                index,
                doc_type,
                instance
            )
        )


def _unique(validator, ref, instance, schema):
    # type: (CustomDraft4Validator, Sequence[str], dict, dict) -> None
    if not validator.index or not validator.doc_type:
        yield ValidationError('index or doc_type need to be set for "unique(-together)" validator')

    is_create = '_id' not in instance
    is_update = not is_create

    # built query for either "unique" or "unique-together" case
    for _ref in ref:
        if isinstance(_ref, list) or isinstance(_ref, set):
            # NONE of the keys present? ok, we don't care
            if not any(key in instance for key in _ref):
                continue

            # only SOME of the keys present? error :(
            if not all(key in instance for key in _ref):
                raise ValidationError(
                    "unique-together property {} needs all "
                    "or none of it's fields to be set: {}".format(_ref, instance)
                )

            # ALL keys are present
            query = reduce(operator.and_, [Q('match', **{'{}.raw'.format(key): instance[key]}) for key in _ref])
        else:
            if _ref not in instance:
                continue
            query = Q('match', **{'{}.raw'.format(_ref): instance[_ref]})

        # hits is a list because we only control this one path, there are many ways
        # how the data could already have become inconsistent in the datastore
        hits, _ = validator.datastore.search_documents(
            validator.index,
            validator.doc_type,
            query.to_dict(),
            refresh=True,
        )

        if is_create and len(hits) > 0:
            yield ValidationError(
                'unique property {} conflicts with existing object(s): {}'.format(_ref, hits)
            )
        elif is_update and len(hits) > 0:
            if any(hit['_id'] != instance['_id'] for hit in hits):
                yield ValidationError(
                    'unique property {} conflicts with existing object: {}'.format(_ref, hits)
                )


def _file(validator, ref, instance, schema):
    # type: (CustomDraft4Validator, Sequence[str], str, dict) -> None

    file_path = Path(validator.upload_path).joinpath(instance.lstrip('/'))

    if not file_path.exists():
        yield ValidationError(
            'invalid file referenced (non-existant/unreadable): {}'.format(file_path)
        )


def is_valid_address(address):
    # https://developers.google.com/maps/documentation/geocoding/intro#Results
    return address.raw['geometry']['location_type'] == 'ROOFTOP'


def _check_address(address, matches):
    # no match
    if not matches:
        yield ValidationError(
            'failed to validate address \'{}\': 0 possible matches'.format(
                address,
            )
        )

    # not unique
    if not len(matches) == 1:
        yield ValidationError(
            'failed to validate address \'{}\': {} possible matches'.format(
                address,
                len(matches),
            )
        )
    else:
        match = matches[0]

    # not valid
    if not is_valid_address(match):
        yield ValidationError(
            'failed to validate address \'{}\': not specific enough'.format(
                address,
                len(matches),
            )

        )


def _check_geo_point(given, checked, threshold):
    drift = distance(given, checked).meters

    if drift > threshold:
        yield ValidationError(
            'failed to validate geo point {}: {} (> {}) meters from matched'
            ' location {}'.format(given, drift, threshold, checked)
        )


def _check_geolocation(validator, ref, instance, schema):
    default_deviation = 50

    if instance.get(ref['override_field']):
        # Check has been overridden
        return

    address = instance.get(ref['address_field'])
    if not address:
        # we cannot validate anything without an address string
        raise ValidationError(
            '`{}` field is required for geo location check'.format(
                ref['address_field']
            )
        )

    # resolve the given address
    matches = app.geocode(address)

    # check address
    for error in _check_address(address, matches):
        yield error

    # check geo point if present
    geo_point = instance.get(ref['geopoint_field'])
    max_deviation = ref.get('geopoint_deviation', default_deviation)

    if geo_point:
        for error in _check_geo_point(Point(geo_point), matches[0].point, max_deviation):
            yield error


validators = {
    'required': _required,
    'x-required': _required,
    'file': _file,
    'x-file': _file,
    'fkey': _fkey,
    'x-fkey': _fkey,
    'unique': _unique,
    'x-unique': _unique,
    'unique-together': _unique,
    'x-unique-together': _unique,
    'x-check-geolocation': _check_geolocation,
}

_CustomDraft4Validator = extend(Draft4Validator, validators, str('draft4'))


class CustomDraft4Validator(_CustomDraft4Validator):
    def __init__(self, *args, **kwargs):
        self.datastore = kwargs.pop('datastore')
        self.upload_path = kwargs.pop('upload_path')

        self.index = kwargs.pop('index', None)
        self.doc_type = kwargs.pop('doc_type', None)

        super(CustomDraft4Validator, self).__init__(*args, **kwargs)
