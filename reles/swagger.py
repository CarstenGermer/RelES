
# whitelist of possible operation field names, see:
# http://swagger.io/specification/#pathItemObject
_OPERATION_VERBS = (
    'get', 'put', 'post', 'delete', 'options', 'head', 'patch'
)


DEFAULT_SECURITY_REQUIREMENTS = [
    {'jwt': []}  # references `securityDefintions`
]


def _get_responses(index, doc_type, create=False, collection=False):
    if create:
        status = '201'
    else:
        status = '200'

    definition_ref = '#/definitions/{}'.format(doc_type)

    if collection:
        response = {
            'description': 'list of {}::{} documents'.format(index, doc_type),
            'schema': {
                'type': 'array',
                'items': {
                    '$ref': definition_ref
                }
            }
        }
    else:
        response = {
            'description': 'single {}::{} document'.format(index, doc_type),
            'schema': {
                '$ref': definition_ref
            }
        }

    return {
        status: response,
        '401': {'$ref': '#/responses/unauthorized'},
        '403': {'$ref': '#/responses/forbidden'},
        'default': {'$ref': '#/responses/genericError'}
    }


def _build_paths(index, definitions):
    output = {}
    for doc_type in definitions.keys():
        output['/{}/{}/'.format(index, doc_type)] = {
            'get': {
                'description': 'list all {}::{} documents'.format(index, doc_type),
                'responses': _get_responses(index, doc_type, collection=True),
                'tags': [index, doc_type],
            },
            'post': {
                'description': 'create a new {}::{} document'.format(index, doc_type),
                'responses': _get_responses(index, doc_type, create=True),
                'tags': [index, doc_type],
                'parameters': [{
                    'name': 'body',
                    'in': 'body',
                    'required': True,
                    'schema': {
                        '$ref': '#/definitions/{}'.format(doc_type)
                    }
                }]
            }
        }
        output['/{}/{}/{{id}}'.format(index, doc_type)] = {
            'parameters': [
                {'$ref': '#/parameters/id'}
            ],
            'get': {
                'description': 'retrieve a single {}::{} document'.format(index, doc_type),
                'responses': _get_responses(index, doc_type),
                'tags': [index, doc_type],
            },
            'put': {
                'description': 'update a single {}::{} document'.format(index, doc_type),
                'responses': _get_responses(index, doc_type),
                'tags': [index, doc_type],
                'parameters': [{
                    'name': 'body',
                    'in': 'body',
                    'required': True,
                    'schema': {
                        '$ref': '#/definitions/{}'.format(doc_type)
                    }
                }]
            },
            'delete': {
                'description': 'delete a single {}::{} document'.format(index, doc_type),
                'responses': _get_responses(index, doc_type),
                'tags': [index, doc_type],
            },
        }
        output['/{}/{}/_search'.format(index, doc_type)] = {
            'post': {
                'description': 'search for {}::{} documents'.format(index, doc_type),
                'responses': _get_responses(index, doc_type, collection=True),
                'tags': [index, doc_type],
                'parameters': [{
                    'name': 'body',
                    'in': 'body',
                    'required': True,
                    'schema': {
                        '$ref': '#/definitions/query'
                    }
                }]
            }
        }
        output['/{}/{}/{{id}}/_archive'.format(index, doc_type)] = {
            'parameters': [
                {'$ref': '#/parameters/id'},
                {
                    'name': 'version',
                    'in': 'query',
                    'description': 'retrieve a specific version of a document '
                                   '(repeat for multiple versions)',
                    'required': False,
                    'type':  'integer',
                    'allowEmptyValue': True,
                    'minimum': 1
                }
            ],
            'get': {
                'description': 'list archived versions of a {}::{} document'.format(index, doc_type),
                'responses': _get_responses(index, doc_type, collection=True),
                'tags': [index, doc_type],
            }
        }
    return output


def _build_definitions(definitions):
    result = dict(definitions)

    result['errorModel'] = {
        'type': 'object',
        'required': [
            'message',
        ],
        'properties': {
            'message': {'type': 'string'},
            'errors': {
                'type': 'array',
                'items': {'type': 'string'}
            }
        }
    }
    result['query'] = {
        'type': 'object',
        'description': 'an Elasticsearch [query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)',
        'required': [
            'query',
        ],
        'properties': {
            'query': {'type': 'object'}
        }
    }

    return result


def _build_parameters():
    return {
        'id': {
            'name': 'id',
            'in': 'path',
            'description': 'id of document',
            'required': True,
            'type': 'string'
        }
    }


def _build_responses():
    return {
        # 'noContent': {
        #     'description': 'The server has successfully fulfilled the request and there is no '
        #                    'additional content to send in the response payload body. '
        #                    '(https://httpstatuses.com/204)',
        #     'schema': {'$ref': '#/definitions/errorModel'}
        # },
        'unauthorized': {
            'description': 'The request has not been applied because it lacks valid '
                           'authentication credentials for the target resource. '
                           '(https://httpstatuses.com/401)',
            'schema': {'$ref': '#/definitions/errorModel'}
        },
        'forbidden': {
            'description': 'The server understood the request but refuses to authorize it. '
                           '(https://httpstatuses.com/403)',
            'schema': {'$ref': '#/definitions/errorModel'}
        },
        # 'notFound': {
        #     'description': 'The origin server did not find a current representation for the '
        #                    'target resource or is not willing to disclose that one exists. '
        #                    '(https://httpstatuses.com/404)',
        #     'schema': {'$ref': '#/definitions/errorModel'}
        # },
        #'badRequest': {
        #    'description': 'The server cannot or will not process the request '
        #                   'due to something that is perceived to be a client '
        #                   'error. (https://httpstatuses.com/400).',
        #    'schema': {'$ref': '#/definitions/errorModel'}
        #},
        'genericError': {
            'description': 'unexpected error',
            'schema': {'$ref': '#/definitions/errorModel'}
        },
    }


def _build_tags(paths):
    """
    Collects the tags from all Operations to make it easier for our clients to know them upfront
    """

    tags = set()
    for operations in paths.values():
        for field_name, operation in operations.items():
            # skip any non-operations (e.g. `parameters`)
            if field_name not in _OPERATION_VERBS:
                continue

            tags.update(operation.get('tags', []))

    return [{'name': tag} for tag in tags]


def _build_security_definitions():
    return {
        'jwt': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
        }
    }


def build_swagger_json(endpoint, schema):
    spec = {
        'swagger': '2.0',
        'info': {
            'version': '1.0.0',
            'title': 'RelES',
            'description': 'The RelES API',
        },
        'schemes': [
            'http',
            'https',
        ],
        'consumes': [
            'application/json',
        ],
        'produces': [
            'application/json',
        ],
    }

    if not 'paths' in schema:
        definitions  = schema['definitions']
        paths = _build_paths(endpoint, definitions)

        spec.update({
            'tags': _build_tags(paths),
            'definitions': _build_definitions(definitions),
            'paths': paths,
            'parameters': _build_parameters(),
            'responses': _build_responses(),
            'security': schema['security'],
            'securityDefinitions':_build_security_definitions(),
        })
    else:
        spec.update(schema)

    return spec
