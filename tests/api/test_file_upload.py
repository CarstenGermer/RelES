from hashlib import sha1
import httplib
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


@pytest.mark.usefixtures('live_server')
class TestFileUploadPermission(object):
    def test_upload_forbidden(self, random_file_content, requests):
        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == 403


@pytest.mark.usefixtures('live_server', 'customer_with_media_permissions')
class TestFileUploadContentType(object):
    def test_content_type_not_whitelisted(self, random_file_content, requests):
        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'bad/content')},
            allow_redirects=False
        )

        assert response.status_code == 400

    def test_content_type_does_not_match_detected(self, random_file_content, requests):
        # prepend .pdf magic bytes to content to mess with the detection
        # https://en.wikipedia.org/wiki/Magic_number_%28programming%29#Magic_numbers_in_files
        modified_content = '\25\50\44\46' + random_file_content

        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', modified_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == 400

    def test_content_type_ok(self, random_file_content, requests):
        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == 201

        created = response.json()
        assert 'mime' in created
        assert created['mime'] == 'text/plain'


@pytest.mark.usefixtures('live_server', 'customer_with_media_permissions')
class TestFileUpload(object):
    def test_upload_matches_hash(self, random_file_content, requests):
        expected_hash = sha1(random_file_content).hexdigest()

        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == 201

        created = response.json()
        assert 'sha1' in created
        assert created['sha1'] == expected_hash

    def test_upload_can_download(self, random_file_content, requests):
        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == 201
        assert 'location' in response.headers

        created = response.json()

        assert 'path' in created
        remote_path = created['path'].lstrip('/')

        response = requests.get(
            url_for('download_file', filename=remote_path, _external=True),
            allow_redirects=False
        )

        assert response.status_code == 200
        assert response.content == random_file_content

    def test_upload_gets_charged(self, customer, random_file_content, app, requests):
        assert 'cycles' not in customer

        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, 'text/plain')},
            allow_redirects=False
        )

        assert response.status_code == httplib.CREATED

        customer.refresh()

        assert len(customer.cycles.to_dict()) == 1
        assert customer.cycles['_upload_text'] == app.config['CYCLES_FILE_UPLOAD']

    def test_upload_charges_only_on_success(self, customer, random_file_content, requests):
        assert 'cycles' not in customer

        wrong_mimetype = 'image/jpeg'

        response = requests.post(
            url_for('upload_file', _external=True),
            files={'file': ('random.txt', random_file_content, wrong_mimetype)},
            allow_redirects=False
        )

        assert response.status_code == httplib.BAD_REQUEST

        customer.refresh()

        assert 'cycles' not in customer
