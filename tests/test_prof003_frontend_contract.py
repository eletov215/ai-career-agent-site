from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "resume_builder.html"


def test_photo_data_url_conversion_does_not_fetch_data_url_in_browser():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "const dataUrlToBlob = (dataUrl) =>" in source
    assert "fetch(dataUrl)" not in source
    assert "window.atob(" in source
    assert "new Blob([bytes], {type: contentType})" in source


def test_photo_upload_failure_restores_previous_preview_state():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "const previousPhoto = state.photo;" in source
    assert "const previousPhotoAssetId = state.photoAssetId;" in source
    assert "state.photo = previousPhoto;" in source
    assert "state.photoAssetId = previousPhotoAssetId;" in source
    assert "Не удалось загрузить изображение на сервер." in source
