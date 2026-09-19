#!/usr/bin/env python3
"""Assemble domain files into the self-contained consumer contract."""
import argparse
from pathlib import Path
import yaml
from request_examples import render_request_examples

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


class IndentedDumper(yaml.SafeDumper):
    """Indent block sequences beneath their containing key."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, indentless=False)


def readable_string(dumper, value):
    return dumper.represent_scalar('tag:yaml.org,2002:str', value,
                                   style='|' if '\n' in value else None)


IndentedDumper.add_representer(str, readable_string)


def dump_yaml(document):
    def ordered(value):
        if isinstance(value, list):
            return [ordered(item) for item in value]
        if not isinstance(value, dict):
            return value
        result = {key: ordered(item) for key, item in value.items()}
        schemas = result.get('schemas')
        if isinstance(schemas, dict):
            parents = {name: [] for name in schemas}
            for name, schema in schemas.items():
                for variant in schema.get('oneOf', []) if isinstance(schema, dict) else []:
                    ref = variant.get('$ref') if isinstance(variant, dict) else None
                    target = ref.rsplit('/', 1)[-1] if ref else None
                    if target in parents and target != name:
                        parents[target].append(name)
            arranged, visiting = {}, set()

            def add(name):
                if name in arranged or name in visiting:
                    return
                visiting.add(name)
                for parent in parents[name]:
                    add(parent)
                visiting.remove(name)
                arranged[name] = schemas[name]

            for name in schemas:
                add(name)
            result['schemas'] = arranged
        paths = result.get('paths')
        if isinstance(paths, dict):
            methods = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']
            for path, item in paths.items():
                if not str(path).startswith('/') or not isinstance(item, dict):
                    continue
                # Keep path-level metadata and shared parameters before operations.
                paths[path] = {**{key: value for key, value in item.items() if key not in methods},
                               **{method: item[method] for method in methods if method in item}}
        responses = result.get('responses')
        if isinstance(responses, dict):
            # Only HTTP response maps, not a schema property or a registry of
            # named reusable responses. Keep extensions and default last.
            def is_status(key):
                key = str(key)
                return (len(key) == 3 and key[0] in '12345'
                        and (key[1:].isdigit() or key[1:] == 'XX'))
            if all(is_status(key) or str(key) == 'default' or str(key).startswith('x-')
                   for key in responses):
                result['responses'] = dict(sorted(responses.items(), key=lambda item:
                    (0, str(item[0])) if is_status(item[0]) else
                    (1 if str(item[0]) == 'default' else 2, str(item[0]))))
        return result

    return readable_yaml(yaml.dump(ordered(document), Dumper=IndentedDumper,
                                   sort_keys=False, allow_unicode=True))


def readable_yaml(text):
    """Separate OpenAPI blocks without changing scalars, comments, or key order."""
    breaks = set()
    methods = {'get', 'put', 'post', 'delete', 'options', 'head', 'patch', 'trace'}

    def visit(node, path=()):
        if not isinstance(node, yaml.MappingNode):
            return
        separate = (
            not path
            or path in (('paths',), ('schemas',), ('components',), ('components', 'schemas'))
            or (len(path) == 2 and path[0] == 'paths')
            or (len(path) == 4 and path[0] == 'paths'
                and path[2] in methods and path[3] == 'responses')
        )
        for index, (key, value) in enumerate(node.value):
            if separate and index:
                breaks.add(key.start_mark.line)
            visit(value, path + (key.value,))

    visit(yaml.compose(text, Loader=UniqueLoader))
    lines = []
    for index, line in enumerate(text.splitlines()):
        if index in breaks and lines and lines[-1].strip():
            lines.append('')
        lines.append(line)
    return '\n'.join(lines) + '\n'


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

    def resolve(ref, origin, seen=None):
        path, fragment, target = reference(ref, origin)
        seen = set() if seen is None else seen
        key = (path, fragment)
        if key in seen:
            raise ValueError(f'Cyclic schema alias: {ref}')
        if isinstance(target, dict) and '$ref' in target:
            if set(target) != {'$ref'}:
                raise ValueError('Registry references cannot have siblings')
            return resolve(target['$ref'], path, seen | {key})
        return path, fragment, target

    document = read(source)
    schemas = {}
    schema_targets = {}

    def register(name, value, origin, fragment):
        if name in schemas:
            raise ValueError(f'Duplicate schema name: {name}')
        if isinstance(value, dict) and '$ref' in value:
            if set(value) != {'$ref'}:
                raise ValueError('Registry references cannot have siblings')
            path, fragment, value = resolve(value['$ref'], origin)
        else:
            path = origin
        key = (path, fragment)
        if key in schema_targets:
            raise ValueError(f'Schema target registered more than once: {name}')
        schema_targets[key] = name
        schemas[name] = (value, path)

    for name, value in document.get('components', {}).get('schemas', {}).items():
        register(name, value, source, '/components/schemas/' + name)
    def source_files(extension, kind):
        for filename in document.get(extension, []):
            location = (source.parent / filename).resolve()
            if not location.is_relative_to(source.parent):
                raise ValueError(f'Reference outside source directory: {location}')
            if location.is_dir():
                files = sorted(path for path in location.rglob('*')
                               if path.is_file() and path.suffix in ('.yaml', '.yml'))
                if not files:
                    raise ValueError(f'No {kind} files in source directory: {location}')
            else:
                files = [location]
            for path in files:
                yield path.resolve()

    for path in source_files('x-schema-sources', 'schema'):
        for name, value in read(path)['schemas'].items():
            register(name, value, path, '/schemas/' + name)

    def component_reference(ref, origin):
        path, fragment, _ = resolve(ref, origin)
        name = schema_targets.get((path, fragment))
        if name is not None:
            return '#/components/schemas/' + name
        if path == source and fragment.startswith('/components/') and not fragment.startswith('/components/schemas/'):
            return '#' + fragment
        raise ValueError(f'Reference is not a registered component: {ref}')

    def normalize(value, origin):
        if isinstance(value, list):
            return [normalize(item, origin) for item in value]
        if not isinstance(value, dict):
            return value
        if 'discriminator' in value:
            value = dict(value)
            discriminator = dict(value['discriminator'])
            mapping = {}
            for name, ref in discriminator.get('mapping', {}).items():
                normalized = component_reference(ref, origin)
                if not normalized.startswith('#/components/schemas/'):
                    raise ValueError(f'Discriminator target is not a schema: {ref}')
                mapping[name] = normalized
            if 'mapping' in discriminator:
                discriminator['mapping'] = mapping
            # Mapping values are references, not ordinary strings. Resolve them
            # before recursively normalizing the rest of the schema.
            return {key: discriminator if key == 'discriminator' else normalize(item, origin)
                    for key, item in value.items()}
        if '$ref' in value:
            ref = component_reference(value['$ref'], origin)
            return {key: ref if key == '$ref' else normalize(item, origin)
                    for key, item in value.items()}
        return {key: normalize(item, origin) for key, item in value.items()}

    def entry(value, origin=source):
        if isinstance(value, dict) and '$ref' in value:
            if set(value) != {'$ref'}:
                raise ValueError('Registry references cannot have siblings')
            path, _, target = reference(value['$ref'], origin)
            return normalize(target, path)
        return normalize(value, origin)

    result = {key: normalize(value, source) for key, value in document.items()
              if key not in ('paths', 'components', 'x-schema-sources', 'x-path-sources')}
    result['paths'] = {}
    path_origins = {}

    def add_paths(values, origin):
        for route, value in values.items():
            if route in path_origins:
                raise ValueError(f'Duplicate path: {route} in {origin}; '
                                 f'already declared in {path_origins[route]}')
            path_origins[route] = origin
            result['paths'][route] = entry(value, origin)

    add_paths(document.get('paths', {}), source)
    for path in source_files('x-path-sources', 'path'):
        add_paths(read(path)['paths'], path)
    result['components'] = {
        kind: {key: entry(value) for key, value in values.items()}
        for kind, values in document.get('components', {}).items() if kind != 'schemas'
    }
    result['components'] = {'schemas': {name: normalize(value, origin)
                                      for name, (value, origin) in schemas.items()},
                            **result['components']}
    # Preserve the original top-level ordering for stable consumer hashes.
    ordered_keys = dict.fromkeys('paths' if key == 'x-path-sources' else key
                                 for key in document if key != 'x-schema-sources')
    result = {key: result[key] for key in ordered_keys}
    render_request_examples(result)
    return dump_yaml(result)


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
