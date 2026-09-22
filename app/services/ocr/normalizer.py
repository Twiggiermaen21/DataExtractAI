"""Defensive normalization for structured OCR responses.

The LLM is required to return every requested key, but this final guard keeps
that contract intact when a provider omits a key or returns null.
"""

from collections.abc import Iterable, Mapping


def normalize_extracted_fields(
    value: Mapping | None,
    fields: Iterable[str],
) -> dict[str, str]:
    """Return one string value for every requested field, preserving order."""
    source = value if isinstance(value, Mapping) else {}
    normalized: dict[str, str] = {}

    for field in fields:
        key = str(field)
        raw = source.get(field, "")
        if raw is None:
            normalized[key] = ""
        elif isinstance(raw, list):
            normalized[key] = " ".join(str(item) for item in raw).strip()
        elif isinstance(raw, dict):
            normalized[key] = str(raw)
        else:
            normalized[key] = str(raw).strip()

    return normalized
