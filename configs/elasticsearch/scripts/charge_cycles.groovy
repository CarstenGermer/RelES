// elasticsearch_dsl currently prevents storing of empty objects
if ( !ctx._source.cycles ) {
    ctx._source.cycles = [:]
}

ctx._source.cycles[index] = ctx._source.cycles.get(index, 0) + cycles
