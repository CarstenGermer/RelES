from __future__ import absolute_import, unicode_literals

from json import loads

from flask import Flask
import pytest

from reles.views import jsonify


@pytest.yield_fixture()
def test_client():
    _app = Flask(__name__)

    @_app.route('/string')
    def string_route():
        return jsonify('hello world')

    @_app.route('/dict')
    def dict_route():
        return jsonify({'hello': 'world'})

    @_app.route('/list')
    def list_route():
        return jsonify(['hello', 'world'])

    with _app.app_context():
        yield _app.test_client()


def test_string_encoding(test_client):
    # type: (flask.testing.FlaskClient) -> None

    res = test_client.get('/string')

    assert res.status_code == 200
    assert res.content_type == 'application/json'

    assert loads(res.data) == 'hello world'


def test_dict_encoding(test_client):
    # type: (flask.testing.FlaskClient) -> None

    res = test_client.get('/dict')

    assert res.status_code == 200
    assert res.content_type == 'application/json'

    assert loads(res.data) == {'hello': 'world'}


def test_list_encoding(test_client):
    # type: (flask.testing.FlaskClient) -> None

    res = test_client.get('/list')

    assert res.status_code == 200
    assert res.content_type == 'application/json'

    assert loads(res.data) == ['hello', 'world']
