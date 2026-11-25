import os
from dataclasses import asdict, dataclass
from . import i18n


@dataclass
class CaseBrief:
    name: str = "StageFinder"
    problem: str = "students struggle to find internships"
    audience: str = "university students"
    constraints: str = "Budget under $500; buildable by students in 8 weeks; plain language."
    evidence: str = "12 student interviews and data/feedback.csv; no revenue yet."

    def text(self, language: str = None) -> str:
        return "\n".join([
            f"{i18n.tr('case_name_label', language)}: {self.name}",
            f"{i18n.tr('problem_label', language)}: {self.problem}",
            f"{i18n.tr('target_user_label', language)}: {self.audience}",
            f"{i18n.tr('constraints_label', language)}: {self.constraints}",
            f"{i18n.tr('evidence_label', language)}: {self.evidence}",
        ])

    def dict(self) -> dict:
        return asdict(self)


DEFAULT_CASE = CaseBrief(
    name=os.getenv("LAB_CASE_NAME", "StageFinder"),
    problem=os.getenv("LAB_CASE_PROBLEM", "students struggle to find internships"),
    audience=os.getenv("LAB_CASE_AUDIENCE", "university students"),
    constraints=os.getenv("LAB_CASE_CONSTRAINTS", "Budget under $500; buildable by students in 8 weeks; plain language."),
    evidence=os.getenv("LAB_CASE_EVIDENCE", "12 student interviews and data/feedback.csv; no revenue yet."),
)

_current = DEFAULT_CASE


def set_case(case=None, **fields):
    global _current
    if case is None:
        case = get_case()
    if isinstance(case, dict):
        values = case.dict() if hasattr(case, "dict") else case
        case = CaseBrief(**{**values, **fields})
    elif isinstance(case, CaseBrief) and fields:
        case = CaseBrief(**{**case.dict(), **fields})
    _current = case
    return _current


def get_case() -> CaseBrief:
    return _current


def case_text(case=None, language: str = None) -> str:
    return (case or get_case()).text(language)


def shared_context(extra: str = "", case=None, language: str = None) -> str:
    language = language or i18n.get_language()
    base = "\n".join([
        i18n.tr("shared_case_header", language),
        case_text(case, language),
        "",
        i18n.tr("language_instruction", language, lang=i18n.label(language)),
    ])
    return base + (f"\n\n{i18n.tr('task_specific_context', language)}\n{extra}" if extra.strip() else "")
