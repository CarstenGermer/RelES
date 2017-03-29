from __future__ import absolute_import, print_function

from hashlib import sha1
import httplib
from urlparse import urljoin

from elasticsearch import NotFoundError, TransportError
from elasticsearch_dsl import Index
from flask import (
    current_app,
    g,
    jsonify,
    make_response,
    request,
    send_from_directory,
    url_for
)
from geopy.exc import GeocoderServiceError
from jsonschema import ValidationError
import magic
from ordered_set import OrderedSet
from pathlib2 import Path
from werkzeug.exceptions import BadRequest

from . import auth
from .auth.aliases import AliasType, translate_index, unalias
from .auth.models import Customer
from .modificators import Processor
from .references import assign_to_field_reference, resolve_field_reference
from .swagger import build_swagger_json
from .validators import CustomDraft4Validator, is_valid_address
from .versioning import (
    VersioningException,
    archive_document_version,
    list_document_versions,
    retrieve_document_version,
)


def error_response(code, message, errors=None):
    return jsonify({'message': message, 'errors': errors}), code


# TODO cache validator instances
def _validator(index, doc_type):
    # type: (str, str) -> CustomDraft4Validator

    datastore = current_app.datastore
    schemastore = current_app.schemastore

    upload_path = current_app.config['UPLOAD_MNT']

    schema = schemastore.get_schema(index, doc_type)
    if not schema:
        # try undoing the index aliasing we do for customer permissions
        _index, _, _ = unalias(index)
        schema = schemastore.get_schema(_index, doc_type)

    if not schema:
        # we have no schema to validate against
        raise ValidationError('There is no schema for {}/{}'.format(_index, doc_type))

    return CustomDraft4Validator(
        schema,
        datastore=datastore,
        upload_path=upload_path,
        index=index,
        doc_type=doc_type
    )


# TODO cache processor instances
def _processor(index, doc_type):
    # type: (str, str) -> Processor

    datastore = current_app.datastore
    schemastore = current_app.schemastore

    schema = schemastore.get_schema(index, doc_type)
    if not schema:
        # try undoing the index aliasing we do for customer permissions
        _index, _, _ = unalias(index)
        schema = schemastore.get_schema(_index, doc_type)

    return Processor(schema, datastore=datastore)


@translate_index(AliasType.read)
def list_documents(index, doc_type):
    # type: (str, str) -> flask.app.Response
    refresh = request.args.get('refresh', False)

    datastore = current_app.datastore

    try:
        documents, effort = datastore.list_documents(index=index, doc_type=doc_type, refresh=refresh)
    except NotFoundError:
        # The endpoint is configured (otherwise auth would have intervened) but the index does not exist?
        return error_response(httplib.INTERNAL_SERVER_ERROR, 'configured index not found')

    try:
        # Only charge valid requests
        Customer.charge_cycles(g.customer['_id'], index, effort)
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)
    else:
        return jsonify(documents)


@translate_index(AliasType.write)
def create_document(index, doc_type):
    # type: (str, str) -> flask.Response
    refresh = request.args.get('refresh', False)

    datastore = current_app.datastore

    body = request.get_json()

    if not body:
        return error_response(400, 'no document provided')

    try:
        _validator(index, doc_type).validate(body)
    except ValidationError as e:
        return error_response(400, e.message)

    processed = _processor(index, doc_type).process(body)

    try:
        # Check if billing goes through before actually saving a new document
        # If the op fails, the document is expected to not have been created
        factor = current_app.config['CYCLES_FACTOR_REFRESH'] if refresh else 1
        Customer.charge_cycles(g.customer['_id'], index, factor * current_app.config['CYCLES_CRUD'])
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    try:
        created = datastore.create_document(index=index, doc_type=doc_type, document=processed, refresh=refresh)
    except NotFoundError as error:
        # The index exists (else no validator), but the alias does not.
        return error_response(404, 'index not found')

    archive_document_version(doc_type, created['_id'], created['_version'], created)

    return jsonify(created), 201


@translate_index(AliasType.read)
def retrieve_document(index, doc_type, id):
    # type: (str, str, str) -> flask.Response

    datastore = current_app.datastore

    try:
        document = datastore.get_document(index=index, doc_type=doc_type, id=id)
    except NotFoundError:
        return error_response(404, 'document not found')

    embed_paths = request.args.getlist('embed')
    if embed_paths:
        endpoint, _, _ = unalias(index)
        document = _embed_documents(endpoint, doc_type, document, embed_paths)

    try:
        # Only charge the customer if there is a document to deliver
        Customer.charge_cycles(g.customer['_id'], index, current_app.config['CYCLES_CRUD'])
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)
    else:
        return jsonify(document)


def _embed_documents(index, doc_type, document, paths):

    datastore = current_app.datastore
    schemastore = current_app.schemastore

    # Process each query param
    for path in paths:
        properties = schemastore.get_schema(index, doc_type).get('properties', {})
        fields = path.split('.')

        # Get `x-fkey` spec from nested documents
        for field in fields:
            field_spec = properties.get(field, {})

            if field_spec.get('type') == 'array':
                field_spec = field_spec.get('items', {})

            fkey_spec = field_spec.get('x-fkey', {})

            if fkey_spec:
                properties = schemastore.get_schema(fkey_spec['index'], fkey_spec['doc_type']).get('properties', {})
            else:
                properties = field_spec.get('properties', {})

        if not fkey_spec:
            return error_response(
                httplib.BAD_REQUEST,
                'cannot embed `{}` into {}/{}/{} since it is not configured as'
                ' an `x-fkey`'.format(path, index, doc_type, id)
            )

        # Get `fkey` values (singles or collections) from *all* fields referenced py the path
        resolved_fkey_data = resolve_field_reference(path, None, document)

        embedded_data = []
        for fkey_data in resolved_fkey_data:
            if isinstance(fkey_data, list):
                embedded_data.append(
                    [datastore.get_document(
                        index=fkey_spec['index'],
                        doc_type=fkey_spec['doc_type'],
                        id=fkey
                    ) for fkey in fkey_data]
                )
            else:
                embedded_data.append(
                    datastore.get_document(
                        index=fkey_spec['index'],
                        doc_type=fkey_spec['doc_type'],
                        id=fkey_data
                    )
                )

        # Embed the retrieved documents
        assign_to_field_reference(path, document, embedded_data)

    return document


@translate_index(AliasType.write)
def update_document(index, doc_type, id):
    # type: (str, str, str) -> flask.Response
    refresh = request.args.get('refresh', False)

    datastore = current_app.datastore

    body = request.get_json()

    try:
        _validator(index, doc_type).validate(body)
    except ValidationError as e:
        return error_response(400, e.message)

    processed = _processor(index, doc_type).process(body, id=id)

    try:
        # Check if billing goes through before updating a new document
        # If the op fails, the document is expected to not have been changed
        factor = current_app.config['CYCLES_FACTOR_REFRESH'] if refresh else 1
        Customer.charge_cycles(g.customer['_id'], index, factor * current_app.config['CYCLES_CRUD'])
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    updated = datastore.update_document(index=index, doc_type=doc_type, document=processed, id=id, refresh=refresh)

    archive_document_version(doc_type, id, updated['_version'], updated)

    return jsonify(updated)


@translate_index(AliasType.write)
def delete_document(index, doc_type, id):
    # type: (str, str, str) -> flask.Response
    datastore = current_app.datastore

    try:
        # Check if billing goes through before deleting a document
        # If the op fails, the document is expected to not have been deleted
        Customer.charge_cycles(g.customer['_id'], index, current_app.config['CYCLES_CRUD'])
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    try:
        return jsonify(datastore.delete_document(index=index, doc_type=doc_type, id=id))
    except NotFoundError:
        return error_response(404, 'document not found')


@translate_index(AliasType.read)
def search_documents(index, doc_type):
    # type: (str, str) -> flask.Response

    try:
        # TODO query from GET params?!
        query = request.get_json() or {
            'query': {
                'match_all': {}
            }
        }
    except BadRequest:
        return error_response(400, 'Failed to parse request body as JSON')

    try:
        hits, effort = current_app.datastore.search_documents(index, doc_type, query)
    except TransportError:
        return error_response(400, 'Invalid query')

    try:
        # Only charge valid requests
        Customer.charge_cycles(g.customer['_id'], index, effort)
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)
    else:
        return jsonify(hits)


@translate_index(AliasType.read)
def retrieve_archived_document(index, doc_type, id):
    # type: (str, str, str) -> flask.Response

    # if the conversion fails with a `ValueError`, the
    # [value is dropped](http://werkzeug.pocoo.org/docs/0.11/datastructures/#werkzeug.datastructures.MultiDict.get).
    versions = request.args.getlist('version', type=int)

    if not versions:
        try:
            retrieved = list_document_versions(doc_type, id)
        except VersioningException as error:
            return error_response(httplib.NOT_FOUND, error.message)
    else:
        retrieved = []
        for version in versions:
            try:
                retrieved.append(retrieve_document_version(doc_type, id, version))
            except VersioningException as error:
                return error_response(httplib.NOT_FOUND, error.message)

    try:
        Customer.charge_cycles(
            g.customer['_id'],
            '_get_archived_{}'.format(doc_type),
            current_app.config['CYCLES_GET_ARCHIVED_DOCUMENT'] * len(retrieved)
        )
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    return jsonify(retrieved)


def _get_allowed_mimes(schemastore):
    # type: (reles.persistence.SchemaStore) -> Sequence[str]
    result = set()
    for doc_type, schema in schemastore.list_definitions('media').items():
        result.update(schema.get('x-allowed-mime-types', []))

    return result


@translate_index(AliasType.write)
def upload_file(index):
    # quick permission check
    if not Index(index).exists():
        return error_response(403, 'missing permission to upload files')

    if 'file' not in request.files:
        return error_response(400, 'no file content given')

    uploaded_file = request.files['file']
    given_mime_type = uploaded_file.mimetype

    detected_mime_type = magic.from_buffer(uploaded_file.stream.read(), mime=True)
    uploaded_file.stream.seek(0)

    allowed_mimes = _get_allowed_mimes(current_app.schemastore)

    if (
        detected_mime_type not in allowed_mimes or
        given_mime_type != detected_mime_type
    ):
        # Intentionally be vague: don't spell out the checks
        return error_response(400, 'Invalid file type')

    filename = sha1(uploaded_file.read()).hexdigest()
    uploaded_file.seek(0)

    # Keep published path independent of NFS mount point and document root
    local_path = Path(current_app.config['UPLOAD_MNT']).joinpath(filename[:2])
    local_path.mkdir(exist_ok=True, parents=True)

    target_filename = local_path.joinpath(filename)
    uploaded_file.save(str(target_filename))

    relative_path = str(Path('/').joinpath(filename[:2]).joinpath(filename))
    file_representation = {
        'path': relative_path,
        'mime': detected_mime_type,
        'sha1': filename,
    }

    response = make_response(jsonify(file_representation), 201)
    response.headers['Location'] = urljoin(
        current_app.config['UPLOAD_HOST'],
        '/cdn/files/',
        relative_path
    )

    try:
        Customer.charge_cycles(
            g.customer['_id'],
            '_upload_{}'.format(given_mime_type.split('/')[0]),
            current_app.config['CYCLES_FILE_UPLOAD']
        )
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    return response


def download_file(index, filename):
    # TODO should downloading check permissions like upload does?
    # might be handled by nginx, or heavily cached which would make checks hard/impossible

    return send_from_directory(
        current_app.config['UPLOAD_MNT'],
        filename
    )


def get_swagger_spec(endpoint_):
    schemastore = current_app.schemastore

    if not endpoint_:
        return jsonify({
            endpoint: url_for('swagger_schema', **{'endpoint_': endpoint})
            for endpoint in schemastore.list_endpoints()
        })

    schema = schemastore.get_schema(endpoint_)
    if schema is None:
        return error_response(403, 'endpoint unknown')

    return jsonify(build_swagger_json(endpoint_, schema))


def geocode():
    #TODO: check any kind of permission?

    def _get_admin_areas(address):
        for component in address.raw['address_components']:
            if 'political' in component['types']:
                yield component['long_name']
                yield component['short_name']

    address = request.args.get('address')

    if not address:
        return error_response(
            httplib.BAD_REQUEST,
            'specify a geolocation to lookup in the `address` URL parameter'
        )

    try:
        matches = current_app.geocode(address)
    except GeocoderServiceError as error:
        return error_response(
            httplib.INTERNAL_SERVER_ERROR,
            'failed to lookup geolocation \'{}\': {}'.format(
                address.encode('utf8'),
                error.message
            )
        )

    try:
        Customer.charge_cycles(
            g.customer['_id'],
            '_geocode_address',
            current_app.config['CYCLES_GEOCODING']
        )
    except auth.NotFoundError as error:
        return error_response(httplib.UNAUTHORIZED, error.error)

    if matches:
        return jsonify([
            {
                'formatted_address': match.address,
                'administrative_areas': list(
                    OrderedSet([area for area in _get_admin_areas(match)])
                ),
                'lat': match.latitude,
                'lon': match.longitude,
            }
            for match in matches if is_valid_address(match)
        ])
    else:
        return jsonify([])
