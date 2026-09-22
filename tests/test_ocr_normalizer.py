import json

from app.services.ocr.normalizer import normalize_extracted_fields


def test_normalize_extracted_fields_keeps_all_requested_fields():
    fields = ["field_a", "field_b", "field_c"]
    value = {"field_a": "abc", "field_b": None, "field_c": ["x", "y"]}

    result = normalize_extracted_fields(value, fields)

    assert result == {
        "field_a": "abc",
        "field_b": "",
        "field_c": "x y",
    }


def test_normalize_extracted_fields_handles_missing_keys():
    fields = ["field_a", "field_b"]
    value = {"field_a": "present"}

    result = normalize_extracted_fields(value, fields)

    assert result == {"field_a": "present", "field_b": ""}


def test_normalize_extracted_fields_serializes_dict_values():
    fields = ["field_a"]
    value = {"field_a": {"nested": "value"}}

    result = normalize_extracted_fields(value, fields)

    assert result["field_a"] == "{'nested': 'value'}"
