# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals

from jsonschema import ValidationError
import pytest

from reles.references import (
    assign_to_field_reference,
    resolve_field_reference,
)


class TestTheFieldResolution(object):

    @pytest.fixture
    def full_entity(self):
        return {
            'foo': {
                'bar': {
                    'baz': [
                        {
                            'qux': {
                                'quux': 'corge',
                                'fred': ['plugh', 'xyzzy']
                            }
                        },
                        {
                            'qux': {
                                'quux': 'waldo',
                                'fred': ['thud']
                            }
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def parent_entity(self, full_entity):
        return full_entity['foo']

    def test_can_resolve_absolute_reference(self, parent_entity, full_entity):
        values = resolve_field_reference(
            'foo.bar.baz',
            parent_entity,
            full_entity
        )

        assert values == [full_entity['foo']['bar']['baz']]

    def test_can_resolve_relative_reference(self, parent_entity, full_entity):
        values = resolve_field_reference(
            '.bar.baz',
            parent_entity,
            full_entity
        )

        assert values == [parent_entity['bar']['baz']]

    def test_can_resolve_lists_of_documents(self, parent_entity, full_entity):
        values = resolve_field_reference(
            'foo.bar.baz.qux.quux',
            parent_entity,
            full_entity
        )

        assert values == [
            full_entity['foo']['bar']['baz'][0]['qux']['quux'],
            full_entity['foo']['bar']['baz'][1]['qux']['quux'],
        ]

    def test_can_resolve_lists_in_lists_of_documents(self, parent_entity, full_entity):
        values = resolve_field_reference(
            'foo.bar.baz.qux.fred',
            parent_entity,
            full_entity
        )

        assert values == [
            full_entity['foo']['bar']['baz'][0]['qux']['fred'],
            full_entity['foo']['bar']['baz'][1]['qux']['fred'],
        ]

    def test_gracefully_handles_missing_values(self, parent_entity, full_entity):
        values = resolve_field_reference(
            'grault.garply',
            parent_entity,
            full_entity
        )

        # resolves to a list of no matches
        assert values == []

    def test_can_assign_values(self, full_entity):
        field = 'grault'
        values = ['one', 'two']

        assert field not in full_entity['foo']['bar']['baz'][0]['qux']
        assert field not in full_entity['foo']['bar']['baz'][1]['qux']

        assign_to_field_reference(
            'foo.bar.baz.qux.{}'.format(field),
            full_entity,
            values
        )

        for index in range(len(values)):
            assert full_entity['foo']['bar']['baz'][index]['qux'][field] == values[index]

    def test_cannot_assign_less_values_than_referenced_fields(self, full_entity):
        field = 'grault'
        values = ['one']

        # We will try to map 1 value onto 2 fields
        assert len(values) < len(full_entity['foo']['bar']['baz'])

        with pytest.raises(ReferenceError) as exception_info:
            assign_to_field_reference(
                'foo.bar.baz.qux.{}'.format(field),
                full_entity,
                values
            )

        assert '{} values'.format(len(values)) in exception_info.value.message
        assert '{} documents'.format(len(full_entity['foo']['bar']['baz'])) in exception_info.value.message

    def test_cannot_assign_more_values_than_referenced_fields(self, full_entity):
        field = 'grault'
        values = ['one', 'two', 'three']

        # We will try to map 3 value onto 2 fields
        assert len(values) > len(full_entity['foo']['bar']['baz'])

        with pytest.raises(ReferenceError) as exception_info:
            assign_to_field_reference(
                'foo.bar.baz.qux.{}'.format(field),
                full_entity,
                values
            )

        assert '{} values'.format(len(values)) in exception_info.value.message
        assert '{} documents'.format(len(full_entity['foo']['bar']['baz'])) in exception_info.value.message
