from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ResumeParseError(ValueError):
    """Raised when a resume PDF cannot be safely parsed."""


@dataclass(frozen=True)
class ParsedResume:
    filename: str
    page_count: int
    text: str

    @property
    def character_count(self) -> int:
        return len(self.text)

    @property
    def preview(self) -> str:
        return self.text[:12000]


def parse_resume_pdf(file_bytes: bytes, filename: str) -> ParsedResume:
    if not file_bytes:
        raise ResumeParseError("Файл пустой. Выберите PDF-резюме и повторите загрузку.")

    if not file_bytes.startswith(b"%PDF"):
        raise ResumeParseError("Выбранный файл не является корректным PDF.")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except (PdfReadError, OSError, ValueError) as exc:
        raise ResumeParseError("PDF повреждён или имеет неподдерживаемый формат.") from exc

    if reader.is_encrypted:
        try:
            unlocked = reader.decrypt("")
        except Exception as exc:  # pypdf can raise format-specific exceptions
            raise ResumeParseError("Защищённые паролем PDF пока не поддерживаются.") from exc
        if not unlocked:
            raise ResumeParseError("Защищённые паролем PDF пока не поддерживаются.")

    page_texts: list[str] = []
    for page in reader.pages:
        try:
            page_texts.append((page.extract_text() or "").strip())
        except Exception:
            page_texts.append("")

    text = "\n\n".join(part for part in page_texts if part).strip()
    if not text:
        raise ResumeParseError(
            "В PDF не найден текст. Вероятно, это скан. На следующем этапе добавим распознавание изображений."
        )

    return ParsedResume(
        filename=filename,
        page_count=len(reader.pages),
        text=text,
    )
