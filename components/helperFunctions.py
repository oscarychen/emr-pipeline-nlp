from spacy import registry


@registry.misc("flattenDictionary")
def flattenDictionary(nested, nestKey=None, collector=None):
    '''Flatten a deeply nested dictionary, return list of elements.'''
    if nestKey is None:
        nestKey = 'next'
    if collector is None:
        collector = []

    nested = {**nested}

    nextLevel = nested.get(nestKey)
    collector.append(nested)

    if nextLevel:
        nested.pop(nestKey)
        return flattenDictionary(nextLevel, nestKey, collector)
    else:
        return collector
