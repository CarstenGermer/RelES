from __future__ import absolute_import

from collections import namedtuple
from time import time

from flask import g
from jsonschema import ValidationError

from reles.references import resolve_field_reference

ProcessingContext = namedtuple(
    'ProcessingContext',
    ('datastore', 'doc_id', 'full_entity', 'full_schema')
)


def _log_access(entity, schema, parent, context):
    if entity:
        raise ValidationError("'log_access' entity cannot be overridden manually")

    if not context.doc_id:
        log = {schema['created']: int(time())}
    else:
        log = {schema['updated']: int(time())}

    # This dependency means that the modificator will only work in a request context.
    log[schema['user']] = g.user['email']
    log[schema['customer']] = g.customer['name']

    return log


def _fill_from_fkey(entity, schema, parent, context):
    # type: (Any, dict, ProcessingContext) -> Union[dict, Sequence, str]
    """
    The *fill from foreign key* modifier pulls a related document - or one of it's attributes -
    into the document being processed. This can be useful to make it possible to enrich the indexes
    for the document being processed with data from the related document, essentially denormalizing
    their relationship. This can make certain kind of queries easier or be required to make them
    possible at all.
    """

    def denormalize(id):
        source_document = context.datastore.get_document(_index, _doc_type, id)
        if _field:
            docs = resolve_field_reference(_field, None, source_document)
            return docs[0] if docs else None
        else:
            return source_document

    if entity:
        raise ValidationError("'fill_from_fkey' entity can not be set to anything!")

    _index = schema['source']['index']
    _doc_type = schema['source']['doc_type']
    _field = schema['source'].get('field', '')

    _fkey_field = schema['fkey_field']
    _fkey_values = resolve_field_reference(_fkey_field, parent, context.full_entity)

    if _fkey_values:
        # The fkey(s) pointing at the data to be denormalized are set
        denormalized = []

        for _fkey_data in _fkey_values:
            if isinstance(_fkey_data, list):
                denormalized.extend([denormalize(_id) for _id in _fkey_data])
            else:
                denormalized.append(denormalize(_fkey_data))

        return denormalized
    else:
        return None


def _include_parents(entity, schema, parent, context):
    # type: (list, dict, Any, ProcessingContext) -> Sequence
    def _get_parents(child_id):
        while child_id is not None:
            yield child_id
            child_id = context.datastore.get_document(
                index,
                doc_type,
                child_id
            ).get(parent_field)

    if not entity:
        # Nothing to expand
        return entity

    index = schema['index']
    doc_type = schema['doc_type']
    parent_field = schema['parent_field']

    parents = set()
    for child_id in entity:
        parents.update([id for id in _get_parents(child_id)])

    return list(parents)


class Processor(object):
    _processors = {
        'x-log-access': _log_access,
        'x-fill-from-fkey': _fill_from_fkey,
        'x-include-parents': _include_parents,
    }

    def __init__(self, schema, datastore, processors=None):
        # type: (dict, DataStore, dict) -> None
        super(Processor, self).__init__()

        self._datastore = datastore
        self.schema = schema

        if processors is not None:
            self._processors = processors

    def _process(self, key, schema, entity, parent, context):
        # type: (str, dict, Union[dict, Sequence, str], Union[dict, Sequence, str], ProcessingContext) -> Union[dict, Sequence, str]
        """
        Recursive helper function for process(). Applies processors in a *depth first* manner, if
        no processors are applicable it ends up copying the entity.
        """

        # apply any applicable processors on this entity...
        for processor_name, processor in self._processors.items():
            if processor_name in schema:
                entity = processor(entity, schema[processor_name], parent, context)

        # ...then recurse deeper into the schema/entity
        if schema['type'] == 'object' and isinstance(entity, dict):
            for _key, _schema in schema.get('properties', {}).items():
                # If the field has not been sent, `None` is passed down as the entity.
                # Modifiers will be applied, but recursion stops due to type checks.
                processed = self._process(_key, _schema, entity.get(_key), entity, context)
                if processed is not None:
                    entity[_key] = processed
            return entity
        elif schema['type'] == 'array' and isinstance(entity, list):
            return [self._process(key, schema['items'], _entity, entity, context) for _entity in entity]
        else:
            return entity

    def process(self, entity, id=None):
        # type: (Union[dict, Sequence, str]) -> Union[dict, Sequence, str]
        """
        Applies any configured processors to the given entity (document). The result will always
        be a new object and given entity unmodified, even if no processor was applicable.
        """

        context = ProcessingContext(
            datastore=self._datastore,
            doc_id=id,
            full_entity=entity,
            full_schema=self.schema,
        )

        for key, sub_schema in self.schema['properties'].items():
            processed = self._process(key, sub_schema, entity.get(key, None), entity, context)
            if processed is not None:
                entity[key] = processed

        # TODO: eliminate `return` statement, use `entity` as in-out-parameter
        return entity
