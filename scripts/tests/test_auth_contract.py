"""Auth protocol invariants shared by the provider and generated consumers."""
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bundle import ROOT, bundle


class AuthContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load(bundle())
        cls.paths = cls.document['paths']
        cls.schemas = cls.document['components']['schemas']

    def test_operations_match_agreed_table(self):
        expected = {(method.lower(), '/v1' + path) for method, path in
                    re.findall(r'^\| `(GET|POST|PUT|DELETE|PATCH)` \| `([^`]+)`',
                               (ROOT / 'AUTH_API_DRAFT.md').read_text(), re.MULTILINE)}
        actual = {(method, path) for path, methods in self.paths.items()
                  for method, op in methods.items() if 'auth' in op.get('tags', [])}
        self.assertEqual(expected, actual)
        ids = [op['operationId'] for methods in self.paths.values() for op in methods.values()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(any(path.startswith('/v1/auth/') for path in self.paths))

    def test_registration_data_and_credentials_are_not_accepted_at_start(self):
        self.assertNotIn('/v1/account', self.paths)
        self.assertNotIn('EmailVerificationRequiredRestriction', self.schemas)
        start = self.paths['/v1/authentications']['post']
        self.assertIn({}, start['security'])
        self.assertNotIn('409', start['responses'])
        self.assertEqual('#/components/schemas/AuthenticationResponse',
                         start['responses']['201']['content']['application/json']['schema']['$ref'])
        self.assertNotIn('tokens', self.schemas['AuthenticationResponse']['properties'])
        self.assertEqual(['authenticationToken'], self.schemas['CreateSessionRequest']['required'])
        self.assertEqual({'purpose'}, set(self.schemas['StartAuthenticationRequest']['properties']))
        self.assertNotIn('Registration', self.schemas)
        self.assertEqual({'type', 'email'}, set(self.schemas['RegistrationStepCompletion']['properties']))
        self.assertTrue(self.schemas['PasswordSetupStepCompletion']['properties']['password']['writeOnly'])

    def test_flow_authorization_is_not_resource_id(self):
        for path, operations in self.paths.items():
            if not path.startswith('/v1/authentications/'):
                continue
            for operation in operations.values():
                self.assertTrue(all('flowTokenAuth' in entry for entry in operation['security']))
                self.assertIn({'flowTokenAuth': [], 'bearerAuth': []}, operation['security'])
                header = next(p for p in operation['parameters'] if p['name'] == 'Flow-Token')
                self.assertTrue(header['required'])
        self.assertEqual('header', self.document['components']['securitySchemes']['flowTokenAuth']['in'])

    def test_step_completions_are_typed_and_secret(self):
        proof = self.schemas['CompleteAuthenticationStepRequest']
        self.assertEqual('type', proof['discriminator']['propertyName'])
        for name in ['PasswordVerificationStepCompletion', 'TotpVerificationStepCompletion',
                     'EmailVerificationStepCompletion', 'BackupCodeVerificationStepCompletion',
                     'GoogleVerificationStepCompletion', 'VkVerificationStepCompletion',
                     'PasswordSetupStepCompletion']:
            model = self.schemas[name]
            self.assertFalse(model['additionalProperties'])
            for field in ['password', 'code', 'state', 'idToken']:
                if field in model['properties']:
                    self.assertTrue(model['properties'][field]['writeOnly'])
        self.assertNotIn('login', self.schemas['StartAuthenticationRequest']['properties'])
        self.assertIn('login', self.schemas['PasswordVerificationStepCompletion']['properties'])
        responses = self.paths['/v1/authentications/{id}/steps/{stepId}/completion']['post']['responses']
        self.assertIn('200', responses)
        self.assertNotIn('201', responses)
        self.assertNotIn('attemptId', self.schemas['CompleteAuthenticationStepResponse']['properties'])
        self.assertFalse(any('/challenges' in path or '/attempts' in path or '/submissions' in path
                             for path in self.paths if path.startswith('/v1/authentications')))

    def test_one_use_grants_replace_inline_credentials(self):
        for path, method in [('/account/deletion','post'),('/account/email/verification','post'),
                             ('/account/totp','post'),('/account/totp','delete'),
                             ('/account/passkeys/requests','post'),('/account/passkeys/{id}','delete'),
                             ('/account/backup-codes','post'),('/account/identities/google','post'),
                             ('/account/identities/google','delete')]:
            self.assertEqual([{'bearerAuth': [], 'reauthenticationAuth': []}],
                             self.paths['/v1' + path][method]['security'])
        for name in ['RequestAccountDeletionRequest','RequestEmailChangeRequest','SetPasswordRequest']:
            self.assertNotIn('credentials', self.schemas[name]['properties'])
            self.assertNotIn('oldPassword', self.schemas[name]['properties'])
        self.assertNotIn('ReauthenticationRequest', self.schemas)
        change = self.paths['/v1/account/password']['put']
        self.assertIn({'bearerAuth': []}, change['security'])  # First-password-only exception.

    def test_public_flows_do_not_disclose_account_state(self):
        for path, method in [('/account/password/reset','post')]:
            op = self.paths['/v1' + path][method]
            self.assertEqual([], op['security'])
            self.assertFalse({'401','403','404','409'} & op['responses'].keys())
        refresh = self.paths['/v1/sessions/{id}/tokens']['post']
        self.assertEqual([], refresh['security'])
        self.assertNotIn('404', refresh['responses'])
        self.assertEqual('invalid_refresh_token', refresh['responses']['400']['content']
                         ['application/json']['examples']['invalidRefreshToken']['value']['error'])

    def test_username_availability_requires_session(self):
        op = self.paths['/v1/usernames/{username}/availability']['get']
        self.assertEqual([{'bearerAuth': []}], op['security'])
        self.assertEqual('#/components/responses/Unauthorized', op['responses']['401']['$ref'])
        self.assertIn('403', op['responses'])

    def test_logout_is_bodyless_and_refresh_is_scoped(self):
        uses = [(method, path) for path, methods in self.paths.items()
                for method, op in methods.items()
                if any('refreshTokenAuth' in item for item in op.get('security', []))]
        self.assertEqual([('delete', '/v1/sessions/{id}')], uses)
        for path, operations in self.paths.items():
            if 'delete' in operations and 'auth' in operations['delete'].get('tags', []):
                self.assertNotIn('requestBody', operations['delete'])
        self.assertNotIn('parameters', self.paths['/v1/sessions']['delete'])
        self.assertNotIn('/v1/session', self.paths)

    def test_common_bearer_challenge_and_cache_headers(self):
        for path, operations in self.paths.items():
            for method, op in operations.items():
                if 'auth' not in op.get('tags', []):
                    continue
                for code, response in op['responses'].items():
                    if code == '401':
                        self.assertEqual({'$ref':'#/components/responses/Unauthorized'}, response)
                        self.assertTrue(any('bearerAuth' in item or 'refreshTokenAuth' in item
                                            for item in op['security']))
                    else:
                        if '$ref' in response:
                            response = self.document['components']['responses'][response['$ref'].rsplit('/', 1)[-1]]
                        self.assertIn('Cache-Control', response['headers'])
                        if code == '204': self.assertNotIn('content', response)
                        if code == '429': self.assertIn('Retry-After', response['headers'])
        headers = self.document['components']['responses']['Unauthorized']['headers']
        self.assertTrue(headers['WWW-Authenticate']['required'])
        self.assertIn('Cache-Control', headers)

    def test_credential_display_is_separate_from_secrets(self):
        self.assertNotIn('secret', self.schemas['TotpStatusResponse']['properties'])
        self.assertNotIn('backupCodes', self.schemas['BackupCodesStatusResponse']['properties'])
        self.assertEqual('array', self.schemas['BackupCodesResponse']['properties']['backupCodes']['type'])
        self.assertEqual('required', self.schemas['PasskeyRequestOptions']['properties']['userVerification']['enum'][0])
        self.assertNotIn('publicKey', self.schemas['Passkey']['properties'])
        self.assertNotIn('setupToken', self.schemas['RequestTotpActivationResponse']['properties'])

    def test_email_and_deletion_changes_have_narrow_requests(self):
        self.assertEqual({'email'}, set(self.schemas['RequestEmailChangeRequest']['properties']))
        self.assertEqual({'token'}, set(self.schemas['ConfirmEmailChangeRequest']['properties']))
        self.assertEqual({'deleteSharedData'}, set(self.schemas['UpdateAccountDeletionRequest']['properties']))
        self.assertEqual([{'bearerAuth': []}], self.paths['/v1/account/deletion']['patch']['security'])
        self.assertNotIn('get', self.paths['/v1/account/deletion'])


if __name__ == '__main__':
    unittest.main()
