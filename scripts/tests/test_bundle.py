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


    def discriminator_fixture(self, directory, target='Thing'):
        source = self.fixture(directory)
        nested = source.parent / 'auth/schemas'
        nested.mkdir(parents=True)
        source.write_text(source.read_text().replace('./domain.yaml', './auth/schemas/session.yaml'))
        (nested / 'session.yaml').write_text('''schemas:
  Thing:
    type: object
    properties:
      child:
        $ref: ../../chefbook.yaml#/components/schemas/Thing
    discriminator:
      propertyName: kind
      mapping:
        recursive: ../../chefbook.yaml#/components/schemas/''' + target + '\n')
        return source

    def test_nested_discriminator_mapping_is_self_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            data = yaml.safe_load(bundle(self.discriminator_fixture(directory)))
            model = data['components']['schemas']['Thing']
            self.assertEqual('#/components/schemas/Thing', model['properties']['child']['$ref'])
            self.assertEqual('#/components/schemas/Thing', model['discriminator']['mapping']['recursive'])

    def test_missing_discriminator_target_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyError):
                bundle(self.discriminator_fixture(directory, 'Missing'))

    def test_domain_registry_and_discriminator_without_root_schemas(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            source.write_text('''paths: {}
components: {}
x-schema-sources: [schemas.yaml]
''')
            (source.parent / 'schemas.yaml').write_text('''schemas:
  Thing:
    $ref: ./common.yaml#/schemas/Thing
''')
            (source.parent / 'common.yaml').write_text('''schemas:
  Thing:
    type: object
    properties:
      child:
        $ref: ./schemas.yaml#/schemas/Thing
    discriminator:
      propertyName: kind
      mapping:
        recursive: ./schemas.yaml#/schemas/Thing
''')
            data = yaml.safe_load(bundle(source))
            model = data['components']['schemas']['Thing']
            self.assertNotIn('x-schema-sources', data)
            self.assertEqual('#/components/schemas/Thing', model['properties']['child']['$ref'])
            self.assertEqual('#/components/schemas/Thing', model['discriminator']['mapping']['recursive'])
            source.write_text(source.read_text().replace('[schemas.yaml]', '[schemas.yaml, schemas.yaml]'))
            with self.assertRaisesRegex(ValueError, 'Duplicate schema name'):
                bundle(source)


    def test_schema_directory_discovers_direct_refs_and_unused_models(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            source.write_text('paths: {}\ncomponents: {}\nx-schema-sources: [schemas/]\n')
            schemas = source.parent / 'schemas'
            nested = schemas / 'nested'
            nested.mkdir(parents=True)
            (schemas / 'union.yaml').write_text('''schemas:
  Union:
    oneOf:
      - $ref: nested/variant.yml#/schemas/Variant
    discriminator:
      propertyName: kind
      mapping:
        variant: nested/variant.yml#/schemas/Variant
''')
            (nested / 'variant.yml').write_text('''schemas:
  Variant:
    type: object
    properties:
      child:
        $ref: ../union.yaml#/schemas/Union
  Unused:
    type: string
''')
            data = yaml.safe_load(bundle(source))
            models = data['components']['schemas']
            self.assertEqual({'Union', 'Variant', 'Unused'}, set(models))
            self.assertEqual('#/components/schemas/Variant', models['Union']['oneOf'][0]['$ref'])
            self.assertEqual('#/components/schemas/Variant', models['Union']['discriminator']['mapping']['variant'])
            self.assertEqual('#/components/schemas/Union', models['Variant']['properties']['child']['$ref'])
            (schemas / 'duplicate.yaml').write_text('schemas:\n  Variant:\n    type: string\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate schema name'):
                bundle(source)

    def test_empty_and_outside_schema_directories_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            (source.parent / 'schemas').mkdir()
            source.write_text('paths: {}\ncomponents: {}\nx-schema-sources: [schemas/]\n')
            with self.assertRaisesRegex(ValueError, 'No schema files'):
                bundle(source)
            source.write_text('paths: {}\ncomponents: {}\nx-schema-sources: [../]\n')
            with self.assertRaisesRegex(ValueError, 'outside source directory'):
                bundle(source)



    def test_path_sources_resolve_relative_refs_and_preserve_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            source.write_text('''components: {}
x-path-sources: [auth/paths/]
x-schema-sources: [auth/schemas.yaml]
''')
            paths = source.parent / 'auth/paths'
            paths.mkdir(parents=True)
            (paths.parent / 'schemas.yaml').write_text('schemas:\n  Result:\n    type: object\n')
            route = '''paths:
  /items:
    summary: Items
    get:
      operationId: getItems
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: ../schemas.yaml#/schemas/Result
'''
            (paths / 'items.yaml').write_text(route)
            data = yaml.safe_load(bundle(source))
            self.assertNotIn('x-path-sources', data)
            self.assertNotIn('x-schema-sources', data)
            item = data['paths']['/items']
            self.assertEqual('Items', item['summary'])
            self.assertEqual('#/components/schemas/Result', item['get']['responses']['200']['content']['application/json']['schema']['$ref'])
            # Disjoint methods still duplicate the same resource declaration.
            (paths / 'duplicate.yml').write_text('paths:\n  /items:\n    delete:\n      responses: {}\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate path: /items'):
                bundle(source)
            (paths / 'duplicate.yml').unlink()
            source.write_text(source.read_text() + 'paths:\n  /items: {}\n')
            with self.assertRaisesRegex(ValueError, 'Duplicate path: /items'):
                bundle(source)

    def test_path_source_file_and_missing_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            source.write_text('components: {}\nx-path-sources: [paths.yaml]\n')
            (source.parent / 'paths.yaml').write_text('paths:\n  /health:\n    get:\n      responses:\n        "204":\n          description: Healthy\n')
            self.assertIn('/health', yaml.safe_load(bundle(source))['paths'])
            (source.parent / 'paths.yaml').write_text('paths:\n  /health:\n    $ref: missing.yaml#/paths/health\n')
            with self.assertRaises(FileNotFoundError):
                bundle(source)

    def test_empty_and_outside_path_directories_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'chefbook.yaml'
            (source.parent / 'paths').mkdir()
            source.write_text('components: {}\nx-path-sources: [paths/]\n')
            with self.assertRaisesRegex(ValueError, 'No path files'):
                bundle(source)
            source.write_text('components: {}\nx-path-sources: [../]\n')
            with self.assertRaisesRegex(ValueError, 'outside source directory'):
                bundle(source)



if __name__ == '__main__':
    unittest.main()
