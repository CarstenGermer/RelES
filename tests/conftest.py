# coding: utf-8

from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from contextlib import contextmanager
import httplib
import multiprocessing
import socket
import time

from elasticsearch_dsl import Index
from mock import Mock
from pathlib2 import Path
import pytest
import requests as _requests

from reles import create_app
from reles.auth.models import auth_index as original_auth_index, Customer, User
from reles.auth import utils
from reles.database import db as _db


class LiveServer(object):
    """The helper class uses to manage live server. Handles creation and
    stopping application in a separate process.

    :param app: The application to run.
    :param port: The port to run application.
    """

    def __init__(self, app, port):
        self.app = app
        self.port = port
        self._process = None

    def start(self):
        """Start application in a separate process."""
        self._process = multiprocessing.Process(
            target=lambda app, port: app.run(port=port, use_reloader=False),
            args=(self.app, self.port)
        )
        self._process.start()

        # We must wait for the server to start listening
        while True:
            try:
                _requests.get(self.url(), timeout=5)
                break
            except _requests.ConnectionError:
                continue

    def url(self, url=''):
        """Returns the complete url based on server options."""
        return 'http://127.0.0.1:%d%s' % (self.port, url)

    def stop(self):
        """Stop application process."""
        if self._process:
            self._process.terminate()

    def __repr__(self):
        return '<LiveServer listening at %s>' % self.url()


@pytest.fixture(scope='session')
def random_port():
    """Find a random open port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()

    return port


@pytest.fixture(scope='session')
def live_server_host_name(random_port):
    return '127.0.0.1:{}'.format(random_port)


@pytest.yield_fixture(scope='session')
def app(live_server_host_name):
    """Establish an application context before running the tests."""
    schema_path = Path(__file__).parent.joinpath('schemas')

    _app = create_app(schema_path)
    _app.config['SERVER_NAME'] = live_server_host_name

    original_auth_index.delete()

    ctx = _app.app_context()
    ctx.push()

    yield _app

    ctx.pop()

    for json_file in Path(schema_path).glob('*.json'):
        _app.es.indices.delete(index=json_file.stem, ignore=httplib.NOT_FOUND)


@pytest.yield_fixture(scope='session')
def live_server(app, random_port):
    server = LiveServer(app, random_port)
    server.start()

    yield server

    server.stop()


@pytest.yield_fixture(scope='session')
def db(app):
    _db.create_all()

    yield _db

    _db.drop_all()


@pytest.yield_fixture(scope='function')
def db_session(db):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    db.session = session

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.yield_fixture
def auth_index():
    index = Index('auth')
    index.create()

    Customer.init(index=index._name)
    User.init(index=index._name)

    yield index

    index.delete()


@pytest.yield_fixture
def customer(auth_index):
    with named_customer('kattegat', auth_index) as c:
        yield c


@pytest.yield_fixture
def another_customer(auth_index):
    with named_customer('vikings', auth_index) as c:
        yield c


@contextmanager
def named_customer(name, auth_index):
    _customer = Customer(name=name, permissions={})
    _customer.save(index=auth_index._name, refresh=True)

    yield _customer

    # update reference
    _customer.refresh()
    _customer.delete(index=auth_index._name)


@pytest.yield_fixture
def user(auth_index, customer, another_customer):
    _user = User(
        email='ragnar@kattegat.dk',
        customers=[customer.name, another_customer.name]
    )
    _user.save(index=auth_index._name, refresh=True)

    yield _user

    _user.delete(index=auth_index._name, ignore=409)


@pytest.fixture
def valid_jwt(auth_index, user):
    return utils.create_jwt(user, name='Ragnar Lothbrok')


@pytest.fixture
def renewable_jwt(auth_index, user, monkeypatch):
    # create an old token so we can renew it and see a difference in `exp`
    monkeypatch.setattr(utils, 'time', Mock(**{
            'time.return_value': int(time.time()) - 2 ** 12
        })
    )
    return utils.create_jwt(user, name='Ragnar Lothbrok', renewable=True)


@pytest.yield_fixture
def requests(valid_jwt):
    import requests

    s = requests.Session()
    s.headers['Authorization'] = 'Bearer %s' % valid_jwt

    yield s

    s.close()
