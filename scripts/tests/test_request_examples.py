import copy
import json
import re
import sys
import unittest
from pathlib import Path

import yaml
from openapi_schema_validator import OAS30WriteValidator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import bundle
from request_examples import json_requests, named_examples, render_request_examples, validate_request_examples


class RequestExamplesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(bundle())
        cls.requests = {op['operationId']: media
                        for _, _, op, _, media in json_requests(cls.document)}

    def values(self, operation):
        return [example['value'] for _, example in named_examples(self.document, self.requests[operation])]

    def test_every_json_request_has_valid_named_examples(self):
        self.assertGreaterEqual(validate_request_examples(self.document), 100)

    def test_all_examples_are_visible_as_individual_json_blocks(self):
        for _, _, operation, _, media in json_requests(self.document):
            values = [json.loads(text) for text in re.findall(
                r'```json\n(.*?)\n```', operation['description'], re.S)]
            expected = [example['value'] for _, example in named_examples(self.document, media)]
            self.assertEqual(expected, values, operation['operationId'])

    def test_authentication_union_variants_are_covered(self):
        start = self.values('startAuthentication')
        proof = self.values('completeAuthenticationStep')
        cases = {
            'AuthenticationPurpose': [v['purpose'] for v in start],
            'StartAuthenticationStepRequest': self.values('startAuthenticationStep'),
            'CompleteAuthenticationStepRequest': proof,
            'GoogleVerificationStepCompletion': [v for v in proof if v['type'] == 'googleVerification'],
            'StartGoogleVerificationStepRequest': [v for v in self.values('startAuthenticationStep')
                                                   if v['type'] == 'googleVerification'],
        }
        components = self.document['components']
        for name, values in cases.items():
            for index, variant in enumerate(components['schemas'][name]['oneOf']):
                validator = OAS30WriteValidator({'allOf': [variant], 'components': components})
                self.assertTrue(any(validator.is_valid(v) for v in values), (name, index))
        allowed = set(components['schemas']['StartAuthenticationStepRequest']['discriminator']['mapping'])
        self.assertEqual(allowed, {v['type'] for v in self.values('startAuthenticationStep')})

    def test_mixed_provider_credentials_are_rejected(self):
        document = copy.deepcopy(self.document)
        media = document['paths']['/v1/authentications/{id}/steps/{stepId}/completion']['post']['requestBody']['content']['application/json']
        media['examples']['googleIdToken']['value']['code'] = 'not-allowed-with-id-token'
        with self.assertRaisesRegex(ValueError, 'googleIdToken.*violates oneOf'):
            validate_request_examples(document)

    def test_missing_example_field_is_rejected(self):
        document = copy.deepcopy(self.document)
        media = document['paths']['/v1/sessions']['post']['requestBody']['content']['application/json']
        del media['examples']['completedSignIn']['value']['authenticationToken']
        with self.assertRaisesRegex(ValueError, 'completedSignIn.*violates required'):
            validate_request_examples(document)

    def test_literal_backticks_do_not_break_a_json_block(self):
        document = {'paths': {'/example': {'post': {'requestBody': {'content': {
            'application/json': {'examples': {'literal': {
                'summary': 'Literal code fence', 'value': {'text': '```json'}}}}
        }}}}}}
        render_request_examples(document)
        self.assertIn('````json\n', document['paths']['/example']['post']['description'])
