from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

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


COMMON_SKILLS = (
    "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Angular",
    "Flask", "Django", "FastAPI", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "Docker", "Kubernetes", "Git", "Linux", "REST API", "GraphQL",
    "HTML", "CSS", "Excel", "Power BI", "Tableau", "1C", "Битрикс",
    "Figma", "Photoshop", "English", "Английский", "Scrum", "Agile",
    "Machine Learning", "Data Science", "TensorFlow", "PyTorch", "Pandas",
)

ROLE_PATTERNS = (
    (r"python.{0,30}(developer|разработчик)|разработчик.{0,30}python", "Python-разработчик"),
    (r"frontend|front-end|фронтенд", "Frontend-разработчик"),
    (r"backend|back-end|бэкенд", "Backend-разработчик"),
    (r"full[ -]?stack|фуллстек", "Fullstack-разработчик"),
    (r"data analyst|аналитик данных", "Аналитик данных"),
    (r"business analyst|бизнес-аналитик", "Бизнес-аналитик"),
    (r"product manager|продакт", "Продакт-менеджер"),
    (r"project manager|руководитель проектов", "Руководитель проектов"),
    (r"designer|дизайнер", "Дизайнер"),
    (r"sales|продаж", "Специалист по продажам"),
    (r"marketing|маркетолог", "Маркетолог"),
    (r"accountant|бухгалтер", "Бухгалтер"),
)

def build_resume_preview(parsed: ParsedResume) -> dict[str, object]:
    text = parsed.text
    lowered = text.lower()

    profession = "Профиль будет уточнён AI"
    for pattern, title in ROLE_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE | re.DOTALL):
            profession = title
            break

    years = []
    for match in re.finditer(r"(?:опыт(?: работы)?|experience)[^\n]{0,40}?(\d{1,2})\s*(?:год|года|лет|year|years)", lowered):
        value = int(match.group(1))
        if 0 < value < 50:
            years.append(value)
    experience = f"около {max(years)} лет" if years else "будет уточнён при полном анализе"

    skills = []
    for skill in COMMON_SKILLS:
        if skill.lower() in lowered and skill not in skills:
            skills.append(skill)

    return {
        "profession": profession,
        "experience": experience,
        "skills_count": len(skills),
        "skills": skills[:8],
        "page_count": parsed.page_count,
        "character_count": parsed.character_count,
    }
