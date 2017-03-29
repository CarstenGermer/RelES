from __future__ import absolute_import, unicode_literals

from uuid import uuid4

from elasticsearch_dsl import Index
import pytest

from reles.auth import models as auth_models
from reles.auth.aliases import AliasType, get_alias
from reles.auth.exceptions import ConflictError, NotFoundError
from reles.auth.models import Customer, User


@pytest.yield_fixture
def customer_index(app):
    """Initialize the `Customer` doc type."""
    test_index = Index(uuid4().hex)
    test_index.create()
    app.cluster.health(wait_for_status='yellow')

    # monkey patch `auth_index`
    original_auth_index = auth_models.auth_index
    auth_models.auth_index = test_index

    Customer.init(index=test_index._name)
    Customer._doc_type.index = test_index._name

    yield test_index

    auth_models.auth_index = original_auth_index
    test_index.delete()


@pytest.fixture
def customer(customer_index):
    """Instantiate a random `Customer`."""
    customer = Customer(name=uuid4().hex)
    customer.save(index=customer_index._name, refresh=True)

    return customer


@pytest.yield_fixture
def user_index(app):
    """Initialize the `User` doc type."""
    test_index = Index(uuid4().hex)
    test_index.create()
    app.cluster.health(wait_for_status='yellow')

    # monkey patch `auth_index`
    original_auth_index = auth_models.auth_index
    auth_models.auth_index = test_index

    User.init(index=test_index._name)

    yield test_index

    auth_models.auth_index = original_auth_index
    # Remove all `User`s.
    #
    # [Don't use delete-by-query to clean out all or most documents in an
    # index. Rather create a new index...]
    # (https://www.elastic.co/guide/en/elasticsearch/plugins/2.2/plugins-delete-by-query.html)
    #
    # [It is no longer possible to delete the mapping for a type. Instead you
    # should delete the index and recreate it with the new mappings.]
    # (https://www.elastic.co/guide/en/elasticsearch/reference/2.2/indices-delete-mapping.html)
    test_index.delete()


@pytest.fixture
def user(user_index):
    """Create a random `User`."""
    user = User(username=uuid4().hex, email='%s@example.com' % uuid4().hex)
    user.save(index=user_index._name, refresh=True)

    return user


@pytest.yield_fixture(scope='function')
def random_index(app):
    """Provide a random test index."""
    test_index = Index(uuid4().hex)
    test_index.create()
    app.cluster.health(wait_for_status='yellow')

    yield test_index

    test_index.delete()


another_index = random_index
another_user = user


@pytest.mark.usefixtures('customer_index')
class TestTheCustomerModel(object):

    def test_can_retrieve_instance_by_name(self, customer):
        match = Customer.get_by_name(customer.name)
        assert match.to_dict() == customer.to_dict()

    def test_handles_non_existent_customers(self):
        with pytest.raises(NotFoundError):
            Customer.get_by_name(uuid4().hex)

    def test_handles_conflicting_customer_names(self, customer_index, customer):
        Customer(name=customer.name).save(index=customer_index._name, refresh=True)

        with pytest.raises(ConflictError):
            Customer.get_by_name(customer.name)

    def test_can_add_permissions(self, customer_index, customer, random_index, another_index):
        # Setup
        permissions = {
            random_index._name: [
                AliasType.read.name
            ]
        }

        customer.permissions = permissions
        customer.save(index=customer_index._name, refresh=True)

        customer = Customer.get_by_name(customer.name)
        assert customer.permissions == permissions

        # Test
        permissions = {
            random_index._name: [
                AliasType.write.name,
            ],
            another_index._name: [
                AliasType.read.name,
            ],
        }

        customer.add_permissions(permissions)
        customer.save(index=customer_index._name, refresh=True)

        # Check
        merged_permissions = Customer.get_by_name(customer.name).permissions.to_dict()
        assert len(merged_permissions) == 2
        assert random_index._name in merged_permissions
        assert another_index._name in merged_permissions

        assert len(merged_permissions[random_index._name]) == 2
        assert AliasType.read.name in merged_permissions[random_index._name]
        assert AliasType.write.name in merged_permissions[random_index._name]

        assert len(merged_permissions[another_index._name]) == 1
        assert AliasType.read.name in merged_permissions[random_index._name]

    def test_can_remove_permissions(self, customer_index, customer, random_index, another_index):
        # Setup
        permissions = {
            random_index._name: [
                AliasType.write.name,
                AliasType.read.name,
            ],
            another_index._name: [
                AliasType.read.name,
            ],
        }

        customer.permissions = permissions
        customer.save(index=customer_index._name, refresh=True)

        customer = Customer.get_by_name(customer.name)
        assert customer.permissions == permissions

        # Test
        permissions = {
            random_index._name: [
                AliasType.write.name,
            ],
            another_index._name: [
                AliasType.read.name,
            ],
        }

        customer.remove_permissions(permissions)
        customer.save(index=customer_index._name, refresh=True)

        # Check
        merged_permissions = Customer.get_by_name(customer.name).permissions.to_dict()
        assert len(merged_permissions) == 1
        assert random_index._name in merged_permissions

        assert len(merged_permissions[random_index._name]) == 1
        assert AliasType.read.name in merged_permissions[random_index._name]

    def test_can_create_aliases(self, app, customer_index, customer, random_index):
        read_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.read.name
        )
        write_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.write.name
        )

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert not aliases

        customer.permissions = {random_index._name: [AliasType.read.name]}
        customer.save(index=customer_index._name)

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert len(aliases) == 1
        assert read_alias in aliases

        customer.permissions[random_index._name] = [
            AliasType.read.name,
            AliasType.write.name
        ]
        customer.save(index=customer_index._name)

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert len(aliases) == 2
        assert read_alias in aliases
        assert write_alias in aliases

    def test_can_remove_aliases(self, app, customer_index, customer, random_index):
        customer.permissions = {
            random_index._name: [AliasType.read.name, AliasType.write.name]
        }
        customer.save(index=customer_index._name)

        read_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.read.name
        )
        write_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.write.name
        )

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert len(aliases) == 2
        assert read_alias in aliases
        assert write_alias in aliases

        customer.permissions[random_index._name] = [AliasType.read.name]
        customer.save(index=customer_index._name)

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert len(aliases) == 1
        assert read_alias in aliases

        customer.permissions = {}
        customer.save(index=customer_index._name)

        aliases = app.es.indices.get_alias()[random_index._name]['aliases']
        assert not aliases

    def test_can_merge_aliases(self, app, customer_index, customer, random_index, another_index):
        customer.permissions = {
            random_index._name: [AliasType.read.name, AliasType.write.name],
            another_index._name: [AliasType.write.name]
        }
        customer.save(index=customer_index._name)

        random_read_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.read.name
        )
        random_write_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.write.name
        )
        another_read_alias = get_alias(
            another_index._name,
            customer.name,
            AliasType.read.name
        )
        another_write_alias = get_alias(
            another_index._name,
            customer.name,
            AliasType.write.name
        )

        aliases = app.es.indices.get_alias()
        random_aliases = aliases[random_index._name]['aliases']
        other_aliases = aliases[another_index._name]['aliases']

        assert len(random_aliases) == 2
        assert random_read_alias in random_aliases
        assert random_write_alias in random_aliases

        assert len(other_aliases) == 1
        assert another_write_alias in other_aliases

        customer.permissions[random_index._name] = [AliasType.read.name]
        customer.permissions[another_index._name] = [
            AliasType.read.name,
            AliasType.write.name
        ]
        customer.save(index=customer_index._name)

        aliases = app.es.indices.get_alias()
        random_aliases = aliases[random_index._name]['aliases']
        other_aliases = aliases[another_index._name]['aliases']

        assert len(random_aliases) == 1
        assert random_read_alias in random_aliases

        assert len(other_aliases) == 2
        assert another_read_alias in other_aliases
        assert another_write_alias in other_aliases

    def test_handles_inconsistent_aliases(self, app, customer_index, customer, random_index, another_index):
        random_read_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.read.name
        )
        random_write_alias = get_alias(
            random_index._name,
            customer.name,
            AliasType.write.name
        )

        # Setup
        customer.permissions = {
            random_index._name: [AliasType.read.name, AliasType.write.name],
        }
        customer.save(index=customer_index._name)

        app.es.indices.delete_alias(index=random_index._name, name=random_write_alias)

        # Check
        aliases = app.es.indices.get_alias()
        assert len(customer.permissions[random_index._name]) == 2
        assert len(aliases[random_index._name]['aliases']) == 1
        assert random_read_alias in aliases[random_index._name]['aliases']

        # Test
        customer.permissions[random_index._name] = [AliasType.read.name]
        customer.save(index=customer_index._name)

        # Check
        aliases = app.es.indices.get_alias()
        assert len(customer.permissions[random_index._name]) == 1
        assert len(aliases[random_index._name]['aliases']) == 1
        assert random_read_alias in aliases[random_index._name]['aliases']

    def test_can_init_cycles(self, customer):
        assert 'cycles' not in customer

        target = 'some_index'
        cycles = 5

        Customer.charge_cycles(customer.meta.id, target, cycles)

        # refresh customer ref
        customer = Customer.get(id=customer.meta.id)

        assert 'cycles' in customer
        assert len(customer.cycles.to_dict()) == 1
        assert customer.cycles[target] == cycles

    def test_can_update_cycles(self, customer):
        target = 'some_index'
        initial_cycles = 2
        new_cycles = 3

        customer.cycles[target] = initial_cycles
        customer.save()

        Customer.charge_cycles(customer.meta.id, target, new_cycles)

        # refresh customer ref
        customer = Customer.get(id=customer.meta.id)

        assert len(customer.cycles.to_dict()) == 1
        assert customer.cycles[target] == initial_cycles + new_cycles

    def test_can_charge_for_multiple_indexes(self, customer):
        costs = [('foo', 1), ('bar', 2)]
        for cost in costs:
            Customer.charge_cycles(customer.meta.id, cost[0], cost[1])

        # refresh customer ref
        customer = Customer.get(id=customer.meta.id)

        assert len(customer.cycles.to_dict()) == 2
        for cost in costs:
            assert customer.cycles[cost[0]] == cost[1]


    def test_handles_charging_of_invalid_customers(self):
        with pytest.raises(NotFoundError) as exception_info:
            Customer.charge_cycles('DoesNotExist', 'some_index', 5)

        assert exception_info.value.error == 'Invalid customer'


class TestTheUserModel(object):

    def test_can_resolve_unique_emails(self, user_index, user, another_user):
        match = User.get_by_email(user.email)
        assert match == user

    def test_cannot_resolve_nonexistent_email(self, user_index):
        with pytest.raises(NotFoundError):
            User.get_by_email('doesnotexist@example.com')

    def test_cannot_resolve_ambiguous_email(self, user_index, user):
        User(email=user.email).save(index=user_index._name, refresh=True)

        with pytest.raises(ConflictError):
            User.get_by_email(user.email)
