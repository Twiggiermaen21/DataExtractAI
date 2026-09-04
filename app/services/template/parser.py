import os
import unicodedata
from typing import BinaryIO, Optional

from app.dto.iusfully_template import TemplateAnalysisRequestDTO
from app.services.template.exceptions import (
    TemplateAnalysisConfigurationError,
    TemplateFileTooLargeError,
    UnsupportedTemplateFileError,
    EmptyTemplateFileError,
    UnprocessableTemplateFileError
)
from app.services.template.extractors import _TEXT_EXTRACTORS

DEFAULT_MAX_FILE_BYTES = 20 * 1024 * 1024  # 10 MB
MAX_ORIGINAL_FILENAME_LENGTH = 255

ALLOWED_EXTENSIONS = {
    '.txt', '.pdf', '.docx', '.doc', '.rtf', '.odt',
}

ALLOWED_MIME_TYPES = {
    '',
    'text/plain',
    'application/octet-stream',
    'application/x-empty',
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/rtf',
    'text/rtf',
    'application/vnd.oasis.opendocument.text',
}

def _positive_int_from_env(name: str, default: int) -> int:
    raw_value = os.environ.get(name)
    if raw_value is None or not raw_value.strip():
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise TemplateAnalysisConfigurationError(
            f'Zmienna {name} musi byc liczba calkowita'
        ) from exc
    if value <= 0:
        raise TemplateAnalysisConfigurationError(f'Zmienna {name} musi byc dodatnia')
    return value

def _positive_int_argument(name: str, value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise TemplateAnalysisConfigurationError(f'Parametr {name} musi byc dodatnia liczba calkowita')
    return value

def _safe_original_filename(filename: str) -> str:
    if not isinstance(filename, str):
        return ''
    basename = filename.replace('\\\\', '/').rsplit('/', 1)[-1].strip()
    if len(basename) > MAX_ORIGINAL_FILENAME_LENGTH:
        return ''
    if any(unicodedata.category(char) in {'Cc', 'Cf'} for char in basename):
        return ''
    return basename

class UploadedTextFileParser:
    """Validates and extracts text from uploaded document files.

    Supported formats: .txt, .pdf, .docx, .doc, .rtf, .odt
    """

    def __init__(self, max_file_bytes: Optional[int] = None):
        if max_file_bytes is None:
            self.max_file_bytes = _positive_int_from_env(
                'IUSFULLY_TEMPLATE_MAX_FILE_BYTES',
                DEFAULT_MAX_FILE_BYTES,
            )
        else:
            self.max_file_bytes = _positive_int_argument(
                'max_file_bytes',
                max_file_bytes,
            )

    def parse(
        self,
        filename: str,
        stream: BinaryIO,
        mime_type: Optional[str] = None,
    ) -> TemplateAnalysisRequestDTO:
        original_filename = _safe_original_filename(filename)
        if not original_filename:
            raise EmptyTemplateFileError('Nazwa pliku nie moze byc pusta')

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedTemplateFileError(
                f'Nieobslugiwane rozszerzenie pliku: {ext}. '
                f'Dozwolone: {', '.join(sorted(ALLOWED_EXTENSIONS))}'
            )

        normalized_mime = (mime_type or '').split(';', 1)[0].strip().lower()
        if normalized_mime not in ALLOWED_MIME_TYPES:
            raise UnsupportedTemplateFileError(
                f'Nieobslugiwany typ MIME: {normalized_mime}'
            )

        content = stream.read(self.max_file_bytes + 1)
        if len(content) > self.max_file_bytes:
            raise TemplateFileTooLargeError(
                f'Plik przekracza limit {self.max_file_bytes} bajtow'
            )
        if not content:
            raise EmptyTemplateFileError('Plik jest pusty')

        extractor = _TEXT_EXTRACTORS.get(ext)
        if extractor is None:
            raise UnsupportedTemplateFileError(
                f'Brak obslugi ekstrakcji tekstu dla rozszerzenia {ext}'
            )
        text = extractor(content)

        if not text or not text.strip():
            raise UnprocessableTemplateFileError(
                'Plik nie zawiera tekstu do analizy'
            )

        return TemplateAnalysisRequestDTO(
            original_filename=original_filename,
            source_text=text,
        )


