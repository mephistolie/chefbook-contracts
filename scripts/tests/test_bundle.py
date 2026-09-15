import sys
import tempfile
import unittest
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import SOURCE, OUTPUT, UniqueLoader, bundle


class BundleTest(unittest.TestCase):
    def test_delivery_is_current_and_self_contained(self):
        result = bundle()
        self.assertEqual(OUTPUT.read_text(), result)
        document = yaml.safe_load(result)
        def visit(value):
            if isinstance(value, dict):
                if '$ref' in value:
                    self.assertTrue(value['$ref'].startswith('#/components/'))
                for child in value.values(): visit(child)
            elif isinstance(value, list):
                for child in value: visit(child)
        visit(document)

    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate YAML key'):
            yaml.load('paths: {}\npaths: {}\n', Loader=UniqueLoader)

    def fixture(self, directory, target='Thing'):
        source = Path(directory) / 'chefbook.yaml'
        source.write_text('''openapi: 3.0.3
paths: {}
components:
  schemas:
    Thing:
      $ref: './domain.yaml#/schemas/Thing'
''')
        (source.parent / 'domain.yaml').write_text('''schemas:
  Thing:
    type: object
    properties:
      child:
        $ref: './chefbook.yaml#/components/schemas/''' + target + "'\n")
        return source

    def test_recursive_schema_keeps_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            data = yaml.safe_load(bundle(self.fixture(directory)))
            self.assertEqual('#/components/schemas/Thing', data['components']['schemas']['Thing']['properties']['child']['$ref'])

    def test_missing_reference_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyError):
                bundle(self.fixture(directory, 'Missing'))

    def test_outside_reference_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.fixture(directory)
            source.write_text(source.read_text().replace('./domain.yaml', '../outside.yaml'))
            with self.assertRaisesRegex(ValueError, 'outside source directory'):
                bundle(source)


if __name__ == '__main__':
    unittest.main()
