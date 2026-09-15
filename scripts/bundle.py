#!/usr/bin/env python3
"""Assemble domain files into the self-contained consumer contract."""
import argparse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'openapi/src/chefbook.yaml'
OUTPUT = ROOT / 'openapi/chefbook.yaml'


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently losing operations or schemas."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def pointer(document, fragment):
    if not fragment.startswith('/'):
        raise ValueError(f'Expected JSON pointer: #{fragment}')
    for token in fragment[1:].split('/'):
        document = document[token.replace('~1', '/').replace('~0', '~')]
    return document


def bundle(source=SOURCE):
    source = source.resolve()
    documents = {}

    def read(path):
        if not path.is_relative_to(source.parent):
            raise ValueError(f'Reference outside source directory: {path}')
        if path not in documents:
            documents[path] = yaml.load(path.read_text(), Loader=UniqueLoader)
        return documents[path]

    def reference(ref, origin):
        file, separator, fragment = ref.partition('#')
        if not separator or '://' in file:
            raise ValueError(f'Only local file references with JSON pointers are supported: {ref}')
        path = (origin.parent / file).resolve() if file else origin
        target = pointer(read(path), fragment)
        return path, fragment, target

    def normalize(value, origin):
        if isinstance(value, list):
            return [normalize(item, origin) for item in value]
        if not isinstance(value, dict):
            return value
        if '$ref' in value:
            path, fragment, _ = reference(value['$ref'], origin)
            if path != source or not fragment.startswith('/components/'):
                raise ValueError(f'Domain references must use the entry point component registry: {value["$ref"]}')
            return {key: '#' + fragment if key == '$ref' else normalize(item, origin)
                    for key, item in value.items()}
        return {key: normalize(item, origin) for key, item in value.items()}

    def entry(value):
        if isinstance(value, dict) and '$ref' in value:
            if set(value) != {'$ref'}:
                raise ValueError('Registry references cannot have siblings')
            path, _, target = reference(value['$ref'], source)
            return normalize(target, path)
        return normalize(value, source)

    document = read(source)
    result = {key: normalize(value, source) for key, value in document.items()
              if key not in ('paths', 'components')}
    result['paths'] = {key: entry(value) for key, value in document['paths'].items()}
    result['components'] = {
        kind: {key: entry(value) for key, value in values.items()}
        for kind, values in document['components'].items()
    }
    # Preserve the original top-level ordering for stable consumer hashes.
    result = {key: result[key] for key in document}
    return yaml.safe_dump(result, sort_keys=False, allow_unicode=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if the committed bundle is stale')
    args = parser.parse_args()
    data = bundle()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != data:
            raise SystemExit('Contract bundle is stale; run python scripts/bundle.py')
        print('Contract bundle is up to date')
    else:
        OUTPUT.write_text(data)
        print(f'Bundled {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
