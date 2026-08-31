from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Literal, Mapping, Tuple


FormFieldType = Literal['text', 'number', 'date']

ALLOWED_FORM_FIELD_TYPES = {'text', 'number', 'date'}
FIELD_KEY_PATTERN = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
PLACEHOLDER_PATTERN = re.compile(r'^\{\{[a-z][a-z0-9_]{0,63}\}\}$')
PLACEHOLDER_SEARCH_PATTERN = re.compile(r'\{\{[a-z][a-z0-9_]{0,63}\}\}')
MAX_LABEL_LENGTH = 120
MAX_VALUE_LENGTH = 10_000
MAX_SOURCE_FRAGMENTS = 20
MAX_SOURCE_FRAGMENT_LENGTH = 10_000


class DTOValidationError(ValueError):
    """Raised when data cannot be represented by an API DTO."""


def _require_exact_keys(data: Mapping[str, Any], expected: set[str], object_name: str) -> None:
    actual = set(data.keys())
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise DTOValidationError(
            f'Niepoprawne pola obiektu {object_name}; brakujace={missing}, dodatkowe={extra}'
        )


@dataclass(frozen=True)
class TemplateAnalysisRequestDTO:
    original_filename: str
    source_text: str

    def __post_init__(self) -> None:
        if not isinstance(self.original_filename, str) or not self.original_filename.strip():
            raise DTOValidationError('Nazwa pliku nie moze byc pusta')
        if not isinstance(self.source_text, str) or not self.source_text.strip():
            raise DTOValidationError('Plik tekstowy nie moze byc pusty')


@dataclass(frozen=True)
class DetectedTemplateFieldDTO:
    """Internal DTO returned by the LLM before the template is rendered."""

    key: str
    source_fragments: Tuple[str, ...]
    label: str
    type: FormFieldType
    extracted_value: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> 'DetectedTemplateFieldDTO':
        if not isinstance(data, Mapping):
            raise DTOValidationError('Wykryte pole musi byc obiektem JSON')

        _require_exact_keys(
            data,
            {'key', 'source_fragments', 'label', 'type', 'extracted_value'},
            'field',
        )

        key = data['key']
        source_fragments = data['source_fragments']
        label = data['label']
        field_type = data['type']
        extracted_value = data['extracted_value']

        if not isinstance(key, str) or not FIELD_KEY_PATTERN.fullmatch(key):
            raise DTOValidationError(f'Niepoprawny klucz pola: {key!r}')
        if not isinstance(source_fragments, list) or not source_fragments:
            raise DTOValidationError('source_fragments musi byc niepusta lista')
        if len(source_fragments) > MAX_SOURCE_FRAGMENTS:
            raise DTOValidationError('Pole zawiera zbyt wiele fragmentow zrodlowych')
        if any(not isinstance(fragment, str) or not fragment.strip() for fragment in source_fragments):
            raise DTOValidationError('Kazdy fragment zrodlowy musi byc niepustym tekstem')
        if any(len(fragment) > MAX_SOURCE_FRAGMENT_LENGTH for fragment in source_fragments):
            raise DTOValidationError('Fragment zrodlowy jest zbyt dlugi')
        if len(set(source_fragments)) != len(source_fragments):
            raise DTOValidationError('Fragmenty zrodlowe jednego pola nie moga sie powtarzac')
        if not isinstance(label, str) or not label.strip() or len(label) > MAX_LABEL_LENGTH:
            raise DTOValidationError('Etykieta pola jest pusta lub zbyt dluga')
        if label != label.strip():
            raise DTOValidationError('Etykieta pola nie moze zawierac skrajnych spacji')
        if any(unicodedata.category(char) == 'Cc' for char in label):
            raise DTOValidationError('Etykieta pola zawiera znak sterujacy')
        if any(char in '<>{}' for char in label):
            raise DTOValidationError('Etykieta pola zawiera niedozwolony znak')
        if not isinstance(field_type, str) or field_type not in ALLOWED_FORM_FIELD_TYPES:
            raise DTOValidationError(f'Nieobslugiwany typ pola: {field_type!r}')
        if not isinstance(extracted_value, str) or not extracted_value.strip():
            raise DTOValidationError('Wyodrebniona wartosc nie moze byc pusta')
        if len(extracted_value) > MAX_VALUE_LENGTH:
            raise DTOValidationError('Wyodrebniona wartosc jest zbyt dluga')

        if field_type == 'number':
            try:
                parsed_number = Decimal(extracted_value)
            except InvalidOperation as exc:
                raise DTOValidationError('Pole number musi zawierac liczbe dziesietna') from exc
            if not parsed_number.is_finite():
                raise DTOValidationError('Pole number musi zawierac skonczona liczbe')

        if field_type == 'date':
            try:
                date.fromisoformat(extracted_value)
            except ValueError as exc:
                raise DTOValidationError('Pole date musi miec format YYYY-MM-DD') from exc

        return cls(
            key=key,
            source_fragments=tuple(source_fragments),
            label=label,
            type=field_type,
            extracted_value=extracted_value,
        )

    @property
    def placeholder(self) -> str:
        return '{{' + self.key + '}}'

    def to_form_field(self) -> 'TemplateFormFieldDTO':
        return TemplateFormFieldDTO(
            placeholder=self.placeholder,
            label=self.label,
            type=self.type,
            extracted_value=self.extracted_value,
        )


@dataclass(frozen=True)
class TemplateFormFieldDTO:
    placeholder: str
    label: str
    type: FormFieldType
    extracted_value: str

    def __post_init__(self) -> None:
        if not isinstance(self.placeholder, str) or not PLACEHOLDER_PATTERN.fullmatch(self.placeholder):
            raise DTOValidationError('Niepoprawny placeholder pola formularza')
        if not isinstance(self.type, str) or self.type not in ALLOWED_FORM_FIELD_TYPES:
            raise DTOValidationError('Niepoprawny typ pola formularza')
        if not isinstance(self.label, str) or not self.label.strip() or len(self.label) > MAX_LABEL_LENGTH:
            raise DTOValidationError('Niepoprawna etykieta pola formularza')
        if not isinstance(self.extracted_value, str) or not self.extracted_value.strip():
            raise DTOValidationError('Niepoprawna wartosc pola formularza')

    def to_dict(self) -> Dict[str, str]:
        return {
            'placeholder': self.placeholder,
            'label': self.label,
            'type': self.type,
            'extracted_value': self.extracted_value,
        }


@dataclass(frozen=True)
class TemplateAnalysisResponseDTO:
    original_filename: str
    template_text: str
    form_fields: Tuple[TemplateFormFieldDTO, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.original_filename, str) or not self.original_filename.strip():
            raise DTOValidationError('Nazwa pliku odpowiedzi nie moze byc pusta')
        if not isinstance(self.template_text, str) or not self.template_text.strip():
            raise DTOValidationError('Tekst szablonu nie moze byc pusty')
        if not isinstance(self.form_fields, tuple):
            raise DTOValidationError('form_fields musi byc krotka DTO')
        if any(not isinstance(field, TemplateFormFieldDTO) for field in self.form_fields):
            raise DTOValidationError('form_fields zawiera niepoprawny element')

        expected_placeholders = {field.placeholder for field in self.form_fields}
        if len(expected_placeholders) != len(self.form_fields):
            raise DTOValidationError('Placeholdery odpowiedzi musza byc unikalne')
        actual_placeholders = set(PLACEHOLDER_SEARCH_PATTERN.findall(self.template_text))
        if actual_placeholders != expected_placeholders:
            raise DTOValidationError('Pola formularza nie odpowiadaja placeholderom szablonu')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_filename': self.original_filename,
            'template_text': self.template_text,
            'form_fields': [field.to_dict() for field in self.form_fields],
        }
