"""Enforce extensible JSON body shapes across all domains."""
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import bundle, pointer


class BodyShapesTest(unittest.TestCase):
    def test_no_top_level_json_arrays(self):
        document = yaml.safe_load(bundle())

        def check(schema, seen=frozenset()):
            self.assertNotEqual('array', schema.get('type'))
            ref = schema.get('$ref')
            if ref and ref not in seen:
                check(pointer(document, ref[1:]), seen | {ref})
            for composition in ('oneOf', 'anyOf', 'allOf'):
                for variant in schema.get(composition, []):
                    check(variant, seen)

        for path, operations in document['paths'].items():
            for method, operation in operations.items():
                bodies = [operation.get('requestBody', {}), *operation['responses'].values()]
                for body in bodies:
                    seen = set()
                    while '$ref' in body:
                        ref = body['$ref']
                        self.assertNotIn(ref, seen, 'Cyclic body reference')
                        seen.add(ref)
                        body = pointer(document, ref[1:])
                    for media, value in body.get('content', {}).items():
                        if media == 'application/json' or media.endswith('+json'):
                            with self.subTest(path=path, method=method):
                                check(value['schema'])


if __name__ == '__main__':
    unittest.main()
