from uuid import uuid4

from flask import url_for
import pytest


@pytest.fixture
def random_file_content():
    return 'Hello File Content! %s\n' % uuid4().hex

# TODO is there merit in actually sending a file with complex binary data instead?
# @pytest.yield_fixture
# def temporary_file():
#     _temporary_file = TemporaryFile()
#     _temporary_file.write('Hello File! %s\n' % uuid4().hex)
#     _temporary_file.flush()
#     _temporary_file.seek(0)
#
#     yield _temporary_file
#
#     _temporary_file.close()


@pytest.fixture
def random_title():
    return 'title_' + uuid4().hex


@pytest.fixture
def uploaded_file_path(requests, random_file_content):
    response = requests.post(
        url_for('upload_file', _external=True),
        files={'file': ('random.txt', random_file_content, 'text/plain')},
        allow_redirects=False
    )

    assert response.status_code == 201

    return response.json()['path'].lstrip('/')


@pytest.mark.usefixtures('live_server', 'customer_with_media_permissions')
class TestMediaObjectCreate(object):
    def test_can_create_picture_for_existing_file(self, uploaded_file_path, random_title, requests):
        response = requests.post(
            url_for('document_create', index='media', doc_type='picture', _external=True),
            allow_redirects=False,
            json={
                'title': random_title,
                'sys_filename': uploaded_file_path,
            }
        )

        assert response.status_code == 201

        created = response.json()

        assert created['sys_filename'] == uploaded_file_path
        assert created['title'] == random_title

    def test_can_not_create_picture_for_missing_file(self, random_title, requests):
        response = requests.post(
            url_for('document_create', index='media', doc_type='picture', _external=True),
            allow_redirects=False,
            json={
                'title': random_title,
                'sys_filename': 'does_not_exist_' + uuid4().hex,
            }
        )

        assert response.status_code == 400

        assert 'invalid file referenced' in response.json()['message']

    def test_can_retrieve_created(self, uploaded_file_path, random_title, requests):
        created = requests.post(
            url_for('document_create', index='media', doc_type='picture', _external=True),
            allow_redirects=False,
            json={
                'title': random_title,
                'sys_filename': uploaded_file_path,
            }
        ).json()

        retrieved_response = requests.get(
            url_for(
                'document_retrieve',
                index='media',
                doc_type='picture',
                id=created['_id'],
                _external=True
            ),
            allow_redirects=False,
        )

        assert retrieved_response.status_code == 200
        retrieved = retrieved_response.json()

        assert retrieved['sys_filename'] == uploaded_file_path
        assert retrieved['title'] == random_title
