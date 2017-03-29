# coding: utf-8

"""Models related to the `auth` module."""

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)


import elasticsearch
import elasticsearch_dsl as dsl
from flask import current_app as app

from ..versioning import ArchivingDocType
from .exceptions import ConflictError, NotFoundError
from .aliases import get_alias, unalias


auth_index = dsl.Index('auth')
auth_index.settings(
    number_of_shards=2,
    number_of_replicas=1
)

class Customer(ArchivingDocType):
    """Model a customer."""

    name = dsl.Keyword()
    permissions = dsl.Object()
    cycles = dsl.Object()

    class Meta:
        index = auth_index._name

    @classmethod
    def get_by_name(cls, name):
        # type: (str, dsl.Index) -> reles.auth.models.Customer
        """Get the first customer with the given name."""
        response = cls.search(index=auth_index._name).filter(
            'term',
            name=name
        ).execute()

        if response.hits.total == 0:
            raise NotFoundError(
                'There is no customer with name \'{}\''.format(name)
            )
        elif response.hits.total == 1:
            return response[0]
        else:
            raise ConflictError(
                'Inconsistent data detected: there are {} customers with name'
                ' \'{}\': {}'.format(
                    response.hits.total,
                    name,
                    [user.meta.id for user in response.hits],
                )
            )

    @classmethod
    def charge_cycles(cls, customer_id, target, cycles):
        es = dsl.connections.connections.get_connection(cls._doc_type.using)

        try:
            return es.update(
                index=cls._doc_type.index,
                doc_type=cls._doc_type.name,
                id=customer_id,
                body={
                    'script': {
                        'file': 'charge_cycles',
                        'lang': 'groovy',
                        'params': {
                            'index': target,
                            'cycles': cycles,
                        }
                    }
                }
            )
        except elasticsearch.NotFoundError:
            app.logger.debug(
                'Failed to charge non-existent customer `%s` with %d cycles for'
                ' index `%s`', customer_id, cycles, target
            )
            raise NotFoundError('Invalid customer')

    def add_permissions(self, permissions):
        """Add the given permissions."""
        for index, added in permissions.items():
            self.permissions[index] = list(
                set(self.permissions.to_dict().get(index, [])).union(added)
            )

    def remove_permissions(self, permissions):
        """Remove the given permissions."""
        for index, removed in permissions.items():
            self.permissions[index] = list(
                set(self.permissions.to_dict().get(index, [])).difference(removed)
            )

    def save(self, using=None, index=None, validate=True, **kwargs):
        """Save a customer instance."""
        self._update_aliases()
        super(Customer, self).save(using, index, validate, **kwargs)

    def _update_aliases(self):
        alias_actions = []

        # delete aliases of removed permissions
        #  this encodes knowledge about how aliases are formatted
        affected_indexes = app.es.indices.get_alias('*_%s_*' % self.name)
        for index in affected_indexes:
            permissions_by_index = self.permissions.to_dict().get(index, [])

            for alias in affected_indexes[index]['aliases']:
                _, customer, permission = unalias(alias)
                if customer == self.name and permission not in permissions_by_index:
                    alias_actions.append(
                        self._build_alias_action('remove', index, permission)
                    )

        # create aliases for added permissions
        for index in self.permissions:
            for permission in self.permissions[index]:
                if not app.es.indices.exists_alias(name=get_alias(index, self.name, permission)):
                    alias_actions.append(
                        self._build_alias_action('add', index, permission)
                    )

        if alias_actions:
            app.es.indices.update_aliases(body={'actions': alias_actions})

    def _build_alias_action(self, action, index, permission):
        return {
            action: {
                'index': index,
                'alias': get_alias(index, self.name, permission)
            }
        }

    def refresh(self):
        """Sync the instance with the ES."""
        self.__dict__.update(self.get(self.meta.id).__dict__)


class User(ArchivingDocType):
    """Model a user."""

    email = dsl.Keyword()
    customers = dsl.Keyword()

    class Meta:
        index = auth_index._name

    @classmethod
    def get_by_email(cls, address):
        """Get the first user with the given email."""
        response = cls.search(index=auth_index._name).filter(
            'term',
            email=address
        ).execute()

        if response.hits.total == 0:
            raise NotFoundError(
                'There is no user with email address \'{}\''.format(address)
            )
        elif response.hits.total == 1:
            return response[0]
        else:
            raise ConflictError(
                'Inconsistent data detected: there are {} users with email'
                ' address \'{}\': {}'.format(
                    response.hits.total,
                    address,
                    [user.meta.id for user in response.hits],
                )
            )
