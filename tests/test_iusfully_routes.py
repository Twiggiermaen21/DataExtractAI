import io
import os
import unittest
from unittest.mock import Mock, patch

from app import create_app
from app.dto.iusfully_template import (
    TemplateAnalysisResponseDTO,
    TemplateFormFieldDTO,
)
from app.services.template.service import (
    InvalidLLMResponseError,
    LLMUpstreamError,
)


class IusfullyTemplateRouteTests(unittest.TestCase):
    def setUp(self):
        self.auth_decode = patch(
            'app.core.auth.decorators.decode_jwt',
            return_value={'user_id': 'test-user'},
        )
        self.verify_user = patch('app.core.auth.decorators.VERIFY_USER_IN_DB', False)
        self.auth_decode.start()
        self.verify_user.start()
        self.addCleanup(self.auth_decode.stop)
        self.addCleanup(self.verify_user.stop)

        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {'Authorization': 'Bearer test-token'}

    def test_requires_authentication(self):
        response = self.client.post(
            '/api/iusfully/templates/analyze',
            data={'file': (io.BytesIO(b'Klient: Jan Kowalski'), 'wzor.txt')},
            content_type='multipart/form-data',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.get_json(),
            {'success': False, 'error': 'Brak tokenu autoryzacji'},
        )

    def test_returns_exact_success_contract(self):
        service = Mock()
        service.analyze.return_value = TemplateAnalysisResponseDTO(
            original_filename='wzor.txt',
            template_text='Klient: {{klient_nazwa}}',
            form_fields=(
                TemplateFormFieldDTO(
                    placeholder='{{klient_nazwa}}',
                    label='Nazwa klienta',
                    type='text',
                    extracted_value='Jan Kowalski',
                ),
            ),
        )

        with patch(
            'app.api.template_routes.IusfullyTemplateAnalysisService',
            return_value=service,
        ):
            response = self.client.post(
                '/api/iusfully/templates/analyze',
                data={
                    'file': (
                        io.BytesIO('Klient: Jan Kowalski'.encode('utf-8')),
                        'wzor.txt',
                        'text/plain',
                    ),
                },
                headers=self.headers,
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                'original_filename': 'wzor.txt',
                'template_text': 'Klient: {{klient_nazwa}}',
                'form_fields': [{
                    'placeholder': '{{klient_nazwa}}',
                    'label': 'Nazwa klienta',
                    'type': 'text',
                    'extracted_value': 'Jan Kowalski',
                }],
            },
        )

    def test_rejects_missing_file_and_unsupported_extension(self):
        missing = self.client.post(
            '/api/iusfully/templates/analyze',
            data={},
            headers=self.headers,
            content_type='multipart/form-data',
        )
        unsupported = self.client.post(
            '/api/iusfully/templates/analyze',
            data={'file': (io.BytesIO(b'EXE'), 'wzor.exe', 'application/octet-stream')},
            headers=self.headers,
            content_type='multipart/form-data',
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(missing.get_json()['error_code'], 'missing_file')
        self.assertEqual(unsupported.status_code, 415)
        self.assertEqual(unsupported.get_json()['error_code'], 'unsupported_file')

    def test_rejects_non_multipart_request_and_additional_file(self):
        wrong_content_type = self.client.post(
            '/api/iusfully/templates/analyze',
            json={'file': 'not-a-file'},
            headers=self.headers,
        )
        additional_file = self.client.post(
            '/api/iusfully/templates/analyze',
            data={
                'file': (io.BytesIO(b'Klient: Jan'), 'wzor.txt'),
                'other': (io.BytesIO(b'Inny plik'), 'inny.txt'),
            },
            headers=self.headers,
            content_type='multipart/form-data',
        )

        self.assertEqual(wrong_content_type.status_code, 415)
        self.assertEqual(
            wrong_content_type.get_json()['error_code'],
            'unsupported_media_type',
        )
        self.assertEqual(additional_file.status_code, 400)
        self.assertEqual(additional_file.get_json()['error_code'], 'multiple_files')

    def test_maps_invalid_llm_response_without_leaking_details(self):
        service = Mock()
        service.analyze.side_effect = InvalidLLMResponseError('sekret upstreamu')

        with patch(
            'app.api.template_routes.IusfullyTemplateAnalysisService',
            return_value=service,
        ):
            response = self.client.post(
                '/api/iusfully/templates/analyze',
                data={'file': (io.BytesIO(b'Klient: Jan Kowalski'), 'wzor.txt')},
                headers=self.headers,
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()['error_code'], 'invalid_llm_response')
        self.assertNotIn('sekret upstreamu', response.get_data(as_text=True))

    def test_rejects_request_over_configured_limit(self):
        with patch.dict(
            os.environ,
            {'IUSFULLY_TEMPLATE_MAX_FILE_BYTES': '8'},
        ):
            response = self.client.post(
                '/api/iusfully/templates/analyze',
                data={'file': (io.BytesIO(b'a' * 70_000), 'duzy.txt')},
                headers=self.headers,
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.get_json()['error_code'], 'file_too_large')

    def test_returns_429_when_analysis_slots_are_busy(self):
        slots = Mock()
        slots.acquire.return_value = False

        with patch('app.api.template_routes._TEMPLATE_ANALYSIS_SLOTS', slots):
            response = self.client.post(
                '/api/iusfully/templates/analyze',
                data={'file': (io.BytesIO(b'Klient: Jan'), 'wzor.txt')},
                headers=self.headers,
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()['error_code'], 'too_many_requests')
        slots.release.assert_not_called()

    def test_maps_upstream_http_error_to_distinct_code(self):
        service = Mock()
        service.analyze.side_effect = LLMUpstreamError('upstream rejected')

        with patch(
            'app.api.template_routes.IusfullyTemplateAnalysisService',
            return_value=service,
        ):
            response = self.client.post(
                '/api/iusfully/templates/analyze',
                data={'file': (io.BytesIO(b'Klient: Jan'), 'wzor.txt')},
                headers=self.headers,
                content_type='multipart/form-data',
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.get_json()['error_code'], 'llm_upstream_error')


if __name__ == '__main__':
    unittest.main()
