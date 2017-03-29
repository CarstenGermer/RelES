from __future__ import absolute_import

import click
import elasticsearch
from elasticsearch import NotFoundError
from flask import current_app

from reles.auth.utils import create_jwt
from reles.auth.models import Customer, User, auth_index
from reles.auth.aliases import AliasType, get_alias


@click.group()
def customers():
    """Customer Management Commands"""
    pass


@customers.command(name='create')
@click.argument('customer_name')
def create_customer(customer_name):
    """Create a customer."""
    click.secho('Creating customer: %s...' % customer_name, bold=True)
    try:
        customer = Customer.get_by_name(customer_name)
        click.secho('* customer exists already: %s' % customer, fg='red')
    except NotFoundError:
        customer = Customer(name=customer_name, permissions={}, cycles={})
        customer.save()
        click.secho('* customer created: %s' % customer, fg='green')


@customers.command(name='list')
def list_customers():
    """List all customers in attached elasticsearch"""
    click.secho('List of customers:', bold=True)

    customer_list = Customer.search(index=auth_index._name).execute()

    for customer in customer_list:
        click.secho('* customer name: %s' % customer.name, fg='green')


@click.group()
def users():
    """User Management Commands"""
    pass


@users.command(name='create')
@click.argument('email')
@click.argument('customer_names', nargs=-1)
def create_user(email, customer_names):
    """Create an User."""
    click.secho('Creating user: %s' % email, bold=True)

    for customer_name in customer_names:
        try:
            Customer.get_by_name(customer_name)
        except NotFoundError:
            click.secho('* customer does not exist: %s' % customer_name, fg='red')
            raise click.Abort()

    try:
        user = User.get_by_email(email)
        click.secho('* user exists already: %s' % user, fg='red')
    except NotFoundError:
        user = User(email=email, customers=customer_names)
        user.save()
        click.secho('* user created: %s' % user, fg='green')


@users.command(name='list')
def list_users():
    """List all users."""
    click.secho('Listing users...', bold=True)

    for user in User.search():
        click.secho('%s' % user, fg='yellow')


@users.command()
@click.argument('email')
def by_email(email):
    """Retrieve User by email."""
    click.secho('Getting user by email: %s' % email, bold=True)
    try:
        user = User.get_by_email(email)
        click.secho('* Found: %s' % user, fg='green')
    except NotFoundError:
        click.secho('* Does not exist!', fg='red')


@users.command()
@click.argument('email')
@click.option('--renewable', is_flag=True, default=False, help='Create a renewable token [default: False]')
def jwt(email, renewable):
    """Generate JWT for User."""
    try:
        user = User.get_by_email(email)
    except NotFoundError:
        click.secho('* Does not exist!', fg='red')
    else:
        click.echo(create_jwt(user, renewable=renewable))


@click.group()
def permissions():
    """Permission Management Commands"""
    pass


def _validate_permissions(ctx, param, value):
    """Make sure indices and permissions exist."""
    valid_permissions = AliasType.__members__.keys()

    permissions = {}
    for index, permission in [grant.split('=', 2) for grant in value]:
        index_permissions = permissions.get(index, set())
        index_permissions.add(permission)
        permissions[index] = index_permissions

    for index in permissions:
        if not current_app.es.indices.exists(index):
            raise click.BadParameter('There is no index "{}"!'.format(index))

        for permission in permissions[index]:
            if permission not in valid_permissions:
                raise click.BadParameter(
                    'Invalid permission \'{}\' for index \'{}\': choose one'
                    ' of {}'.format(permission, index, valid_permissions)
                )

    return permissions


@permissions.command()
@click.argument('customer_name')
@click.argument('grants', nargs=-1, required=True, callback=_validate_permissions)
def grant(customer_name, grants):
    """Grant (add) customer permissions.

    Usage:

        auth grant CUSTOMER_NAME index1=read index1=write index2=read
    """
    try:
        customer = Customer.get_by_name(customer_name)
    except NotFoundError:
        click.secho('* customer does not exist: %s' % customer_name, fg='red')
        raise click.Abort()
    else:
        click.secho(
            '* granting new permissions to "%s"' % customer_name,
            bold=True
        )

    customer.add_permissions(grants)
    customer.save()


@permissions.command()
@click.argument('customer_name')
@click.argument('grants', nargs=-1, required=True, callback=_validate_permissions)
def deny(customer_name, grants):
    """Deny (remove) customer permissions.

    Usage:

        auth deny CUSTOMER_NAME index1=read index1=write index2=read
    """
    try:
        customer = Customer.get_by_name(customer_name)
    except NotFoundError:
        click.secho('* customer does not exist: %s' % customer_name, fg='red')
        raise click.Abort()
    else:
        click.secho(
            '* denying previous permissions from "%s"' % customer_name,
            bold=True
        )

    customer.remove_permissions(grants)
    customer.save()


@permissions.command(name='list')
@click.argument('customer_name')
def list_permissions(customer_name):
    """Show permissions for a given customer."""
    try:
        customer = Customer.get_by_name(customer_name)
    except NotFoundError:
        click.secho('* customer does not exist: %s' % customer_name, fg='red')
        raise click.Abort()

    click.secho(
        'Listing customer permissions "<index>=<permission> (<alias exists>)":',
        bold=True
    )

    # TODO get from context instead!
    es = current_app.es  # type: elasticsearch.Elasticsearch

    permissions = customer.permissions.to_dict()
    if len(permissions) <= 0:
        click.secho('* No existing permissions', fg='yellow')
    else:
        for index in permissions:
            for permission in permissions[index]:
                alias_exists = es.indices.exists_alias(
                    index,
                    get_alias(index, customer_name, permission)
                )
                click.secho(
                    '- %s=%s (%s)' % (index, permission, alias_exists),
                    fg='green' if alias_exists else 'yellow'
                )
