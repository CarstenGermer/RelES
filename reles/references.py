# coding: utf-8

from __future__ import absolute_import, print_function, unicode_literals


def resolve_field_reference(path, parent_entity, full_entity):
    """Handle 'paths' to subfields."""
    prefix, level = _split_path(path)

    entity = parent_entity if prefix and not prefix[0] else full_entity

    documents = _descend_through_levels(entity, prefix)

    return [document[level] for document in documents if level in document]


def assign_to_field_reference(path, document, values):
    """Assign a value to each field the path references."""
    prefix, level = _split_path(path)

    documents = _descend_through_levels(document, prefix)

    if len(documents) != len(values):
        raise ReferenceError(
            'cannot map {} values to the {} documents referenced by {}'.format(
                len(values),
                len(documents),
                path,
            )
        )

    for i, document in enumerate(documents):
        document[level] = values[i]


def _split_path(path):
    fields = path.split('.')
    return fields[:-1], fields[-1]


def _descend_through_levels(document, levels):
    current_level = [document]

    for field in filter(None, levels):
        temp = []
        for doc in current_level:
            try:
                next_level = doc[field]
            except KeyError:
                continue

            if isinstance(next_level, list):
                for new_doc in next_level:
                    temp.append(new_doc)
            else:
                temp.append(next_level)
        current_level = temp

    return current_level


