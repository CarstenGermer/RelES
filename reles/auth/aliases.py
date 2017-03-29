from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from enum import Enum
from flask import g
import wrapt

AliasType = Enum('AliasType', ['read', 'write'])

_ALIAS_PATTERNS = {
    AliasType.read.name: '{}_{}_search',
    AliasType.write.name: '{}_{}_index',
}


def translate_index(functionality):
    """
    A decorator for index translation.

    Returns a decorator that translates an index at runtime.
    """
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        if 'customer' not in g:
            raise Exception('Cannot translate an index without a customer')

        _index = kwargs.pop('index')
        alias = get_alias(_index, g.customer['name'], functionality.name)
        return wrapped(index=alias, *args, **kwargs)

    return wrapper


# TODO @memoize?
def get_alias(index, customer, functionality):
    # type: (str, str, AliasType) -> str
    """Get an alias for a given index."""
    return _ALIAS_PATTERNS[functionality].format(index, customer)


def unalias(alias):
    """Parse the given alias into its components."""
    # type: (str) -> Tuple[str, str, AliasType]
    index, customer, suffix = alias.split('_', 2)

    for functionality, pattern in _ALIAS_PATTERNS.items():
        if pattern.endswith(suffix):
            return index, customer, functionality

    raise Exception('Could not unalias: %s' % alias)
