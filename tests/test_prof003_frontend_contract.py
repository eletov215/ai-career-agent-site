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

def test_university_logo_keeps_intrinsic_aspect_ratio_for_pdf_capture():
    css = (TEMPLATE.parents[1] / "static" / "styles.css").read_text(encoding="utf-8")

    marker = ".resume-modern-university-logo img{"
    start = css.index(marker)
    block = css[start:css.index("}", start) + 1]
    assert "width:auto" in block
    assert "height:auto" in block
    assert "max-width:100%" in block
    assert "max-height:100%" in block


def test_education_preview_does_not_repeat_same_university_name_twice():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "const resolvedUniversityName = String(state.universityResolvedName || '').trim();" in source
    assert "normalizedResolvedUniversity.includes(normalizedEducationText)" in source
    assert "const detailsText = duplicateEducation ? '' : educationText;" in source
    assert "educationDetails.hidden = !detailsText;" in source

