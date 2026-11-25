"""Axis 11 (advanced) - FastAPI: turn your AI logic into a service any app can call.
Run:  uvicorn src.api:app --reload      then open http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field
from . import axes
from .context import CaseBrief, DEFAULT_CASE, get_case

app = FastAPI(title="AI Start-up Lab API", version="1.0")


class CaseFields(BaseModel):
    case_name: str = DEFAULT_CASE.name
    case_problem: str = DEFAULT_CASE.problem
    case_audience: str = DEFAULT_CASE.audience
    case_constraints: str = DEFAULT_CASE.constraints
    case_evidence: str = DEFAULT_CASE.evidence

    def brief(self) -> CaseBrief:
        return CaseBrief(name=self.case_name, problem=self.case_problem, audience=self.case_audience,
                         constraints=self.case_constraints, evidence=self.case_evidence)


class IdeaRequest(CaseFields):
    problem: str = Field(..., min_length=5, examples=["students struggle to find internships"])
    n: int = Field(5, ge=1, le=10)


class TextRequest(CaseFields):
    text: str = Field(..., min_length=20)
    audience: str = "a busy investor"
    words: int = Field(80, ge=20, le=300)


class ModelRequest(CaseFields):
    price: float = 9.0
    cac: float = 12.0
    monthly_churn: float = Field(0.06, gt=0, lt=1)
    new_per_month: int = 40
    months: int = Field(12, ge=1, le=36)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/case")
def case():
    return {"case": get_case().dict()}


@app.post("/brainstorm")
def brainstorm(req: IdeaRequest):
    brief = req.brief()
    return {"case": brief.dict(), "ideas": axes.brainstorm(req.problem, req.n, case=brief)}


@app.post("/summarize")
def summarize(req: TextRequest):
    brief = req.brief()
    return {"case": brief.dict(), "summary": axes.summarize(req.text, req.audience, req.words, case=brief)}


@app.post("/model")
def model(req: ModelRequest):
    brief = req.brief()
    table, unit = axes.financial_model(req.price, req.cac, req.monthly_churn, req.new_per_month, req.months, case=brief)
    return {"case": brief.dict(), "unit_economics": unit, "months": table.to_dict(orient="records")}
