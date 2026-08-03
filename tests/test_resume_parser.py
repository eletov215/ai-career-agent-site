from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from services.resume_parser import (
    ParsedResume,
    ResumeParseError,
    build_resume_preview,
    parse_resume_pdf,
)


def make_text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    content = StreamObject()
    content._data = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    page[NameObject("/Contents")] = writer._add_object(content)

    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_parse_resume_rejects_empty_and_non_pdf_files():
    with pytest.raises(ResumeParseError, match="Файл пустой"):
        parse_resume_pdf(b"", "resume.pdf")
    with pytest.raises(ResumeParseError, match="не является корректным PDF"):
        parse_resume_pdf(b"not a pdf", "resume.pdf")


def test_parse_resume_extracts_text_from_valid_pdf():
    parsed = parse_resume_pdf(
        make_text_pdf("Python developer experience 5 years SQL Docker"),
        "resume.pdf",
    )

    assert parsed.filename == "resume.pdf"
    assert parsed.page_count == 1
    assert "Python developer" in parsed.text


def test_parse_resume_rejects_image_only_or_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)

    with pytest.raises(ResumeParseError, match="не найден текст"):
        parse_resume_pdf(buffer.getvalue(), "blank.pdf")


def test_build_resume_preview_detects_role_experience_and_skills():
    parsed = ParsedResume(
        filename="resume.pdf",
        page_count=2,
        text="Python developer. Experience 7 years. Python, SQL, Docker and Git.",
    )

    preview = build_resume_preview(parsed)

    assert preview["profession"] == "Python-разработчик"
    assert preview["experience"] == "около 7 лет"
    assert preview["page_count"] == 2
    assert set(preview["skills"]) >= {"Python", "SQL", "Docker", "Git"}
