import io
import json
import unittest

import requests
from urllib3.exceptions import ReadTimeoutError

from app.dto.iusfully_template import TemplateAnalysisRequestDTO
from app.services.iusfully_template_service import (
    InvalidLLMResponseError,
    IusfullyTemplateAnalysisService,
    LLMTimeoutError,
    LLMUnavailableError,
    TemplateFileTooLargeError,
    UnprocessableTemplateFileError,
    UnsupportedTemplateFileError,
    UploadedTextFileParser,
)


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else json.dumps(payload or {})

    def json(self):
        return self._payload


class StreamingTimeoutResponse:
    status_code = 200
    headers = {}

    def iter_content(self, chunk_size=8192):
        urllib3_timeout = ReadTimeoutError(None, None, 'Read timed out.')
        raise requests.exceptions.ConnectionError(urllib3_timeout)

    def close(self):
        pass


class CloseFailureResponse:
    def __init__(self, response, stream_error=None):
        self.status_code = response.status_code
        self.headers = getattr(response, 'headers', {})
        self.text = getattr(response, 'text', '')
        self._stream_error = stream_error
        self.close_calls = 0

    def iter_content(self, chunk_size=8192):
        if self._stream_error is not None:
            raise self._stream_error
        yield self.text.encode('utf-8')

    def close(self):
        self.close_calls += 1
        raise OSError('socket close failed')


def successful_llm_response(fields):
    content = json.dumps({'fields': fields}, ensure_ascii=False)
    return FakeResponse(
        payload={
            'choices': [
                {'message': {'content': content}},
            ],
        },
    )


class UploadedTextFileParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = UploadedTextFileParser(max_file_bytes=32)

    def test_parses_utf8_bom_and_removes_client_path(self):
        parsed = self.parser.parse(
            r'C:\fakepath\wezwanie.TXT',
            io.BytesIO(b'\xef\xbb\xbfZa\xc5\xbc\xc3\xb3\xc5\x82\xc4\x87'),
            'application/octet-stream',
        )

        self.assertEqual(parsed.original_filename, 'wezwanie.TXT')
        self.assertEqual(parsed.source_text, 'Zażółć')

    def test_rejects_file_over_limit(self):
        with self.assertRaises(TemplateFileTooLargeError):
            self.parser.parse('test.txt', io.BytesIO(b'a' * 33), 'text/plain')

    def test_rejects_non_txt_extension(self):
        with self.assertRaises(UnsupportedTemplateFileError):
            self.parser.parse('test.exe', io.BytesIO(b'text'), 'application/octet-stream')

    def test_rejects_invalid_utf8_and_binary_content(self):
        with self.assertRaises(UnsupportedTemplateFileError):
            self.parser.parse('test.txt', io.BytesIO(b'\xff\xfe'), 'text/plain')

        with self.assertRaises(UnsupportedTemplateFileError):
            self.parser.parse('test.txt', io.BytesIO(b'abc\x00def'), 'text/plain')

    def test_rejects_whitespace_only_text(self):
        with self.assertRaises(UnprocessableTemplateFileError):
            self.parser.parse('test.txt', io.BytesIO(b'  \r\n\t'), 'text/plain')


class IusfullyTemplateAnalysisServiceTests(unittest.TestCase):
    def _service(self, response=None, post_func=None, **overrides):
        if post_func is None:
            post_func = lambda *args, **kwargs: response
        return IusfullyTemplateAnalysisService(
            api_url='http://llm.test/v1/chat/completions',
            model='test-model',
            timeout_seconds=5,
            max_tokens=1000,
            post_func=post_func,
            **overrides,
        )

    def test_builds_template_from_exact_source_fragments(self):
        source_text = (
            'Wezwanie dla Jan Kowalski Sp. z o.o.\n'
            'Kwota: 1 500,50 zł. Termin: 15.09.2026.\n'
            'Odbiorca: Jan Kowalski Sp. z o.o.'
        )
        fields = [
            {
                'key': 'klient_nazwa',
                'label': 'Nazwa klienta',
                'type': 'text',
                'source_fragments': ['Jan Kowalski Sp. z o.o.'],
                'extracted_value': 'Jan Kowalski Sp. z o.o.',
            },
            {
                'key': 'kwota_do_zaplaty',
                'label': 'Kwota do zapłaty',
                'type': 'number',
                'source_fragments': ['1 500,50'],
                'extracted_value': '1500.50',
            },
            {
                'key': 'termin_platnosci',
                'label': 'Termin płatności',
                'type': 'date',
                'source_fragments': ['15.09.2026'],
                'extracted_value': '2026-09-15',
            },
        ]
        service = self._service(successful_llm_response(fields))

        result = service.analyze(TemplateAnalysisRequestDTO('wezwanie.txt', source_text))
        payload = result.to_dict()

        self.assertEqual(payload['original_filename'], 'wezwanie.txt')
        self.assertEqual(payload['template_text'].count('{{klient_nazwa}}'), 2)
        self.assertIn('Kwota: {{kwota_do_zaplaty}} zł', payload['template_text'])
        self.assertIn('Termin: {{termin_platnosci}}', payload['template_text'])
        self.assertEqual(
            [field['type'] for field in payload['form_fields']],
            ['text', 'number', 'date'],
        )
        self.assertEqual(payload['form_fields'][1]['extracted_value'], '1500.50')
        self.assertEqual(payload['form_fields'][2]['extracted_value'], '2026-09-15')

    def test_sends_document_as_json_data_with_strict_schema(self):
        captured = {}

        def fake_post(url, **kwargs):
            captured['url'] = url
            captured.update(kwargs)
            return successful_llm_response([])

        source_text = 'To jest treść dokumentu, a nie instrukcja.'
        self._service(post_func=fake_post).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', source_text)
        )

        request_payload = captured['json']
        user_data = json.loads(request_payload['messages'][1]['content'])
        self.assertEqual(user_data['document_text'], source_text)
        self.assertTrue(request_payload['response_format']['json_schema']['strict'])
        self.assertEqual(request_payload['temperature'], 0)
        self.assertTrue(captured['stream'])

    def test_empty_field_list_returns_unchanged_document(self):
        source_text = 'Dokument bez danych do podmiany.'
        result = self._service(successful_llm_response([])).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', source_text)
        )

        self.assertEqual(result.template_text, source_text)
        self.assertEqual(result.form_fields, ())

    def test_rejects_fragment_not_present_in_document(self):
        fields = [{
            'key': 'klient_nazwa',
            'label': 'Nazwa klienta',
            'type': 'text',
            'source_fragments': ['Nieistniejąca firma'],
            'extracted_value': 'Nieistniejąca firma',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Firma: Istniejąca firma')
            )

    def test_rejects_value_inconsistent_with_source_fragment(self):
        fields = [{
            'key': 'kwota',
            'label': 'Kwota',
            'type': 'number',
            'source_fragments': ['100,00'],
            'extracted_value': '999.00',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Kwota: 100,00 zł')
            )

    def test_does_not_replace_source_inside_a_larger_word(self):
        fields = [{
            'key': 'klient_imie',
            'label': 'Imię klienta',
            'type': 'text',
            'source_fragments': ['Jan'],
            'extracted_value': 'Jan',
        }]
        source_text = 'Klient: Jan. Kontakt: Janusz.'

        result = self._service(successful_llm_response(fields)).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', source_text)
        )

        self.assertEqual(
            result.template_text,
            'Klient: {{klient_imie}}. Kontakt: Janusz.',
        )

    def test_does_not_replace_text_inside_a_larger_identifier(self):
        fields = [{
            'key': 'numer_sprawy',
            'label': 'Numer sprawy',
            'type': 'text',
            'source_fragments': ['123'],
            'extracted_value': '123',
        }]
        source_text = 'Sprawa: 123. Powiązana sprawa: ABC-123/2026.'

        result = self._service(successful_llm_response(fields)).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', source_text)
        )

        self.assertEqual(
            result.template_text,
            'Sprawa: {{numer_sprawy}}. Powiązana sprawa: ABC-123/2026.',
        )

    def test_does_not_replace_number_inside_a_thousands_group(self):
        fields = [{
            'key': 'kwota_pierwsza',
            'label': 'Pierwsza kwota',
            'type': 'number',
            'source_fragments': ['500'],
            'extracted_value': '500',
        }]
        source_text = "Kwota A: 500. Kwota B: 1 500. Kwota C: 1'500."

        result = self._service(successful_llm_response(fields)).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', source_text)
        )

        self.assertEqual(
            result.template_text,
            "Kwota A: {{kwota_pierwsza}}. Kwota B: 1 500. Kwota C: 1'500.",
        )

    def test_rejects_number_fragment_that_contains_currency(self):
        fields = [{
            'key': 'kwota',
            'label': 'Kwota',
            'type': 'number',
            'source_fragments': ['1 500,50 zł'],
            'extracted_value': '1500.50',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Kwota: 1 500,50 zł.')
            )

    def test_rejects_number_fragment_with_sentence_punctuation(self):
        fields = [{
            'key': 'kwota',
            'label': 'Kwota',
            'type': 'number',
            'source_fragments': ['500.'],
            'extracted_value': '500',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Kwota: 500.')
            )

    def test_rejects_identifier_fragment_that_contains_its_label(self):
        fields = [{
            'key': 'klient_nip',
            'label': 'NIP klienta',
            'type': 'text',
            'source_fragments': ['NIP podatnika: 123-456-78-90'],
            'extracted_value': '1234567890',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO(
                    'dokument.txt',
                    'NIP podatnika: 123-456-78-90',
                )
            )

    def test_rejects_identifier_fragment_with_sentence_punctuation(self):
        fields = [{
            'key': 'klient_nip',
            'label': 'NIP klienta',
            'type': 'text',
            'source_fragments': ['123-456-78-90.'],
            'extracted_value': '1234567890',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'NIP: 123-456-78-90.')
            )

    def test_does_not_treat_generic_rachunek_number_as_a_bank_account(self):
        fields = [{
            'key': 'numer_rachunku',
            'label': 'Numer rachunku',
            'type': 'text',
            'source_fragments': ['FV/12/2026'],
            'extracted_value': 'FV/12/2026',
        }]

        result = self._service(successful_llm_response(fields)).analyze(
            TemplateAnalysisRequestDTO(
                'dokument.txt',
                'Numer rachunku: FV/12/2026.',
            )
        )

        self.assertEqual(
            result.template_text,
            'Numer rachunku: {{numer_rachunku}}.',
        )

    def test_rejects_date_fragment_with_static_suffix(self):
        fields = [{
            'key': 'termin_platnosci',
            'label': 'Termin płatności',
            'type': 'date',
            'source_fragments': ['15.09.2026 r.'],
            'extracted_value': '2026-09-15',
        }]

        with self.assertRaises(InvalidLLMResponseError):
            self._service(successful_llm_response(fields)).analyze(
                TemplateAnalysisRequestDTO(
                    'dokument.txt',
                    'Termin płatności: 15.09.2026 r.',
                )
            )

    def test_maps_requests_timeout(self):
        def timeout(*args, **kwargs):
            raise requests.exceptions.Timeout()

        with self.assertRaises(LLMTimeoutError):
            self._service(post_func=timeout).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )

    def test_maps_streaming_read_timeout(self):
        with self.assertRaises(LLMTimeoutError):
            self._service(StreamingTimeoutResponse()).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )

    def test_close_failure_does_not_replace_success(self):
        response = CloseFailureResponse(successful_llm_response([]))

        result = self._service(response).analyze(
            TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
        )

        self.assertEqual(result.form_fields, ())
        self.assertEqual(response.close_calls, 1)

    def test_close_failure_does_not_replace_response_size_error(self):
        response = CloseFailureResponse(successful_llm_response([]))

        with self.assertRaises(InvalidLLMResponseError):
            self._service(response, max_response_bytes=10).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )

        self.assertEqual(response.close_calls, 1)

    def test_close_failure_does_not_replace_stream_timeout(self):
        urllib3_timeout = ReadTimeoutError(None, None, 'Read timed out.')
        wrapped_timeout = requests.exceptions.ConnectionError(urllib3_timeout)
        response = CloseFailureResponse(
            successful_llm_response([]),
            stream_error=wrapped_timeout,
        )

        with self.assertRaises(LLMTimeoutError):
            self._service(response).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )

        self.assertEqual(response.close_calls, 1)

    def test_rejects_oversized_llm_response(self):
        with self.assertRaises(InvalidLLMResponseError):
            self._service(
                successful_llm_response([]),
                max_response_bytes=10,
            ).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )

    def test_maps_llm_rate_limit_to_unavailable(self):
        with self.assertRaises(LLMUnavailableError):
            self._service(FakeResponse(status_code=429)).analyze(
                TemplateAnalysisRequestDTO('dokument.txt', 'Klient: Jan Kowalski')
            )


if __name__ == '__main__':
    unittest.main()
