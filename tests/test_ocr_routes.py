import io
import pytest
from unittest.mock import Mock, patch

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def auth_mocks():
    with patch("app.core.auth.decorators.decode_jwt", return_value={"user_id": "test-user"}):
        with patch("app.core.auth.decorators.VERIFY_USER_IN_DB", False):
            yield


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_pipeline():
    with patch("app.api.ocr_routes.get_pipeline") as mock_get:
        with patch("app.api.ocr_routes.unload_pipeline") as mock_unload:
            pipeline = Mock()
            pipeline.fields = []
            mock_get.return_value = pipeline
            yield pipeline


def test_requires_authentication(client):
    response = client.post(
        "/api/process_ocr_iusfully",
        data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": "test"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 401


def test_missing_files(client, auth_headers):
    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"fields": "test"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "Brak plikow"


def test_empty_filename(client, auth_headers):
    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"files": (io.BytesIO(b""), ""), "fields": "test"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "Nie wybrano plikow"


def test_missing_fields(client, auth_headers):
    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"files": (io.BytesIO(b"data"), "test.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "Brak pol do ekstrakcji"


def test_pipeline_unavailable(client, auth_headers):
    with patch("app.api.ocr_routes.get_pipeline", return_value=None):
        response = client.post(
            "/api/process_ocr_iusfully",
            headers=auth_headers,
            data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": "test"},
            content_type="multipart/form-data",
        )
        assert response.status_code == 500
        assert response.json["error"] == "Nie mozna polaczyc z LM Studio"


def test_pipeline_init_error(client, auth_headers):
    with patch("app.api.ocr_routes.get_pipeline", side_effect=Exception("LM ded")):
        response = client.post(
            "/api/process_ocr_iusfully",
            headers=auth_headers,
            data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": "test"},
            content_type="multipart/form-data",
        )
        assert response.status_code == 500
        assert response.json["error"] == "Blad: LM ded"


def test_success_single_file(client, auth_headers, mock_pipeline):
    result_mock = Mock()
    result_mock.extracted_data = {"field1": "value1"}
    result_mock.text = "some text"
    mock_pipeline.predict.return_value = [result_mock]

    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": '["field1"]'},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json["success"] is True
    assert response.json["processed"] == ["test.pdf"]
    assert len(response.json["documents"]) == 1
    assert response.json["documents"][0]["filename"] == "test.pdf"
    assert response.json["documents"][0]["fields"] == {"field1": "value1"}
    assert len(response.json["errors"]) == 0


def test_no_data_extracted_returns_422(client, auth_headers, mock_pipeline):
    result_mock = Mock()
    result_mock.extracted_data = None
    result_mock.text = ""
    mock_pipeline.predict.return_value = [result_mock]

    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": "field1"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert response.json["success"] is False
    assert len(response.json["errors"]) == 1
    assert (
        "Nie zwrocil" in response.json["errors"][0]["error"]
        or "nie zwrocil danych" in response.json["errors"][0]["error"]
    )


def test_prediction_error_returns_422(client, auth_headers, mock_pipeline):
    mock_pipeline.predict.side_effect = Exception("OCR failed")

    response = client.post(
        "/api/process_ocr_iusfully",
        headers=auth_headers,
        data={"files": (io.BytesIO(b"data"), "test.pdf"), "fields": "field1"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 422
    assert response.json["success"] is False
    assert len(response.json["errors"]) == 1
    assert response.json["errors"][0]["file"] == "test.pdf"
    assert response.json["errors"][0]["error"] == "OCR failed"
