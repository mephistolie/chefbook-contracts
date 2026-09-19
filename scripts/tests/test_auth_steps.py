"""Schema boundaries for typed steps; server transition rules need runtime tests."""
import sys
import unittest
from pathlib import Path

import yaml
from openapi_schema_validator import OAS30ReadValidator, OAS30WriteValidator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import bundle


class AuthenticationStepsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(bundle())
        cls.components = cls.document['components']

    def valid(self, name, value, read=False):
        validator = OAS30ReadValidator if read else OAS30WriteValidator
        schema = {'allOf': [{'$ref': '#/components/schemas/' + name}], 'components': self.components}
        return validator(schema).is_valid(value)

    def test_start_accepts_only_purpose(self):
        value = {'purpose': {'type': 'signUp'}}
        self.assertTrue(self.valid('StartAuthenticationRequest', value))
        for field, data in [('registration', {'email': 'a@example.com'}), ('email', 'a@example.com'),
                            ('password', 'secret'), ('username', 'chef'), ('provider', 'google')]:
            self.assertFalse(self.valid('StartAuthenticationRequest', {**value, field: data}), field)

    def test_registration_email_does_not_accept_credentials_or_wrappers(self):
        value = {'type': 'registration', 'email': 'a.b@example.com'}
        self.assertTrue(self.valid('CompleteAuthenticationStepRequest', value))
        for field, data in [('password', 'secret'), ('username', 'chef'), ('provider', 'google'),
                            ('registration', {'email': 'a.b@example.com'}), ('authentication', {}),
                            ('data', {}), ('code', '123456')]:
            self.assertFalse(self.valid('CompleteAuthenticationStepRequest', {**value, field: data}), field)
        self.assertFalse(self.valid('CompleteAuthenticationStepRequest', {'type': 'registration'}))

    def test_create_step_does_not_accept_its_completion_data(self):
        for value in [{'type': 'registration', 'email': 'a@example.com'},
                      {'type': 'passwordSetup', 'password': 'secret'},
                      {'type': 'emailVerification', 'code': '123456'}]:
            self.assertFalse(self.valid('StartAuthenticationStepRequest', value))

    def test_step_type_controls_shape(self):
        self.assertTrue(self.valid('CompleteAuthenticationStepRequest',
                                   {'type': 'passwordSetup', 'password': 'secret'}))
        self.assertFalse(self.valid('CompleteAuthenticationStepRequest',
                                    {'type': 'passwordSetup', 'password': 'secret', 'login': 'a@example.com'}))
        self.assertTrue(self.valid('CompleteAuthenticationStepRequest',
                                   {'type': 'emailVerification', 'code': '012345'}))
        for code in ['12345', '1234567', 'abcdef', 123456]:
            self.assertFalse(self.valid('CompleteAuthenticationStepRequest',
                                        {'type': 'emailVerification', 'code': code}))
        self.assertFalse(self.valid('CompleteAuthenticationStepRequest',
                                    {'method': 'email', 'code': '123456'}))

    def test_provider_creation_modes_are_not_ambiguous(self):
        for value in [
            {'type': 'googleVerification', 'redirectUri': 'https://example.com/oauth'},
            {'type': 'googleVerification', 'credentialType': 'idToken'},
            {'type': 'vkVerification', 'redirectUri': 'https://example.com/oauth'},
        ]:
            self.assertTrue(self.valid('StartAuthenticationStepRequest', value), value)
        for value in [
            {'type': 'googleVerification'},
            {'type': 'googleVerification', 'credentialType': 'idToken', 'redirectUri': 'https://example.com'},
            {'type': 'vkVerification', 'credentialType': 'idToken'},
            {'type': 'emailVerification', 'redirectUri': 'https://example.com'},
        ]:
            self.assertFalse(self.valid('StartAuthenticationStepRequest', value), value)

    def test_all_response_examples_match_response_schemas(self):
        for path, methods in self.document['paths'].items():
            if not path.startswith('/v1/authentications'):
                continue
            for operation in methods.values():
                for response in operation['responses'].values():
                    for media in response.get('content', {}).values():
                        schema = {'allOf': [media['schema']], 'components': self.components}
                        for key, example in media.get('examples', {}).items():
                            errors = list(OAS30ReadValidator(schema).iter_errors(example['value']))
                            self.assertEqual([], errors, (path, key, [e.message for e in errors]))

    def test_response_union_rejects_mixed_step_parameters(self):
        value = {'id': '11111111-1111-4111-8111-111111111111', 'type': 'emailVerification',
                 'status': 'pending', 'expirationTimestamp': '2026-09-19T12:15:00Z', 'codeLength': 6}
        self.assertTrue(self.valid('AuthenticationStep', value, read=True))
        self.assertFalse(self.valid('AuthenticationStep', {**value, 'url': 'https://example.com'}, read=True))
        self.assertFalse(self.valid('AuthenticationStep', {**value, 'code': '123456'}, read=True))

    def test_signup_example_gates_setup_until_email_verified(self):
        op = self.document['paths']['/v1/authentications/{id}/steps/{stepId}/completion']['post']
        examples = op['responses']['200']['content']['application/json']['examples']
        collected = examples['emailCollected']['value']['authentication']
        self.assertEqual([{'type': 'emailVerification'}], collected['next']['options'])
        verified = examples['emailVerified']['value']['authentication']
        self.assertEqual([{'type': 'passwordSetup'}], verified['next']['options'])
        self.assertNotIn('confirmationToken', verified)

    def test_signup_passkey_step_is_not_supported(self):
        self.assertFalse(self.valid('StartAuthenticationStepRequest', {'type': 'passkeyRegistration'}))
        self.assertFalse(self.valid('CompleteAuthenticationStepRequest',
                                    {'type': 'passkeyRegistration', 'name': 'Phone', 'credential': {}}))


if __name__ == '__main__':
    unittest.main()
