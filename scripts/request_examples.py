"""Render named OpenAPI request examples and validate them in write context."""
import json
import re

HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'}


def resolve(document, value):
    seen = set()
    while isinstance(value, dict) and '$ref' in value:
        ref = value['$ref']
        if not ref.startswith('#/') or ref in seen:
            raise ValueError(f'Expected an acyclic local reference: {ref}')
        seen.add(ref)
        value = document
        for token in ref[2:].split('/'):
            value = value[token.replace('~1', '/').replace('~0', '~')]
    return value


def json_requests(document):
    for path, item in document.get('paths', {}).items():
        for method, operation in item.items():
            if method not in HTTP_METHODS:
                continue
            body = resolve(document, operation.get('requestBody', {}))
            for content_type, media in body.get('content', {}).items():
                mime = content_type.partition(';')[0].strip()
                if mime == 'application/json' or mime.endswith('+json'):
                    yield path, method, operation, content_type, media


def named_examples(document, media):
    return [(name, resolve(document, example))
            for name, example in media.get('examples', {}).items()]


def render_request_examples(document):
    """Append visible JSON blocks from examples; never store a second source copy."""
    sections = {}
    for path, method, operation, content_type, media in json_requests(document):
        examples = named_examples(document, media)
        if not examples:
            continue
        blocks = sections.setdefault((path, method), [])
        for name, example in examples:
            if 'value' not in example:
                raise ValueError(f'{method.upper()} {path}: example {name} needs an inline value')
            title = example.get('summary', name)
            value = json.dumps(example['value'], ensure_ascii=False, indent=2, allow_nan=False)
            # Keep literal backticks inside string values from ending a Markdown fence.
            fence = '`' * max(3, max((len(m) + 1 for m in re.findall(r'`+', value)), default=0))
            blocks.append(f'#### {title}\n\n'
                          + (example['description'] + '\n\n' if example.get('description') else '')
                          + f'Content-Type: `{content_type}`\n\n{fence}json\n{value}\n{fence}')
    for (path, method), blocks in sections.items():
        operation = document['paths'][path][method]
        original = operation.get('description', '').rstrip()
        introduction = ('### Request examples\n\n'
                        'Each block is a separate request scenario. Supply the headers and '
                        'path parameters documented for this operation. Token, code and '
                        'cryptographic values are illustrative; use values issued by your flow.')
        operation['description'] = '\n\n'.join(filter(None, [original, introduction, *blocks]))


def validate_request_examples(document):
    from openapi_schema_validator import OAS30WriteValidator, oas30_format_checker

    count = 0
    for path, method, operation, content_type, media in json_requests(document):
        examples = named_examples(document, media)
        if not examples:
            raise ValueError(f'{method.upper()} {path}: missing named JSON request examples')
        # This root keeps #/components references local, with OAS 3.0 nullable,
        # discriminator and readOnly/writeOnly behavior instead of plain JSON Schema.
        schema = {'allOf': [media['schema']], 'components': document.get('components', {})}
        validator = OAS30WriteValidator(schema, format_checker=oas30_format_checker)
        for name, example in examples:
            if not example.get('summary') or 'value' not in example:
                raise ValueError(f'{method.upper()} {path}: example {name} needs summary and value')
            errors = list(validator.iter_errors(example['value']))
            if errors:
                # Identify the schema location without dumping credential-shaped values.
                error = errors[0]
                location = '/'.join(map(str, error.absolute_path)) or '(root)'
                raise ValueError(f'{method.upper()} {path}, example {name}, {location}: '
                                 f'violates {error.validator}')
            count += 1
    return count
