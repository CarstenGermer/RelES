# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import datetime
import decimal
import json
from time import timezone
import uuid

from flask_sqlalchemy import SQLAlchemy


# stolen & adjusted from DRF:
# https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/utils/encoders.py
class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time/timedelta,
    decimal types, generators and other basic python objects.
    """
    def default(self, obj):
        # For Date Time string spec, see ECMA 262
        # http://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        if isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            # NOTE: we store microseconds with full precision, technically not a valid isostring...
            # if obj.microsecond:
            #     representation = representation[:23] + representation[26:]
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            if timezone and timezone.is_aware(obj):
                raise ValueError("JSON can't represent timezone-aware times.")
            representation = obj.isoformat()
            # NOTE: we store microseconds with full precision, technically not a valid isostring...
            # if obj.microsecond:
            #     representation = representation[:12]
            return representation
        elif isinstance(obj, decimal.Decimal):
            # Serializers will coerce decimals to strings by default.
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif hasattr(obj, 'tolist'):
            # Numpy arrays and array scalars.
            return obj.tolist()
        elif hasattr(obj, '__getitem__'):
            try:
                return dict(obj)
            except:
                pass
        elif hasattr(obj, '__iter__'):
            return tuple(item for item in obj)
        return super(JSONEncoder, self).default(obj)


class SmartJsonSQLAlchemy(SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        options['json_serializer'] = JSONEncoder().encode
        # options['json_deserializer'] = JSONDecoder().decode
        return super(SmartJsonSQLAlchemy, self).apply_driver_hacks(app, info, options)

db = SmartJsonSQLAlchemy()
