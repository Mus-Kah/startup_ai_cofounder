"""One function per axis of the workshop. Read them top to bottom: they follow the start-up journey."""
import re
from pathlib import Path
import pandas as pd
from .context import get_case, shared_context
from .llm import ask, ask_json
from .prompts import build, MENTOR


# 1. BRAINSTORMING - diverge first, filter later
def brainstorm(problem: str, n: int = 8, case=None) -> str:
    return ask(build(MENTOR, f"Propose {n} distinct start-up ideas for this problem: {problem}",
                     context=shared_context(f"Problem focus: {problem}", case),
                     constraints="Budget under $500, buildable by students in 8 weeks, plain language.",
                      fmt="Numbered blocks with fields: Idea, Target user, Cheapest first test, Main risk"))



# 2. RESEARCH - AI plans the research; live facts come from Perplexity / Deep Research (see GUIDES.md)
def research_plan(idea: str, case=None) -> str:
    return ask(build(MENTOR, f"Write a desk-research plan to validate: {idea}",
                     context=shared_context(f"Validation focus: {idea}", case),
                     fmt="10 questions grouped by market, competitors, users, regulation, each with a source type to check"))


# 3. KNOWLEDGE EXTRACTION - unstructured text -> structured data
def extract(text: str, case=None):
    return ask_json(build("a user-research analyst", "Extract insights from this interview.",
                          context=shared_context(f"Interview text:\n{text}", case),
                          constraints="Quote the interviewee verbatim. Invent nothing.",
                          fmt='JSON: {"pains":[str],"needs":[str],"quotes":[str],"willingness_to_pay":str}'))


# 4. SUMMARIZATION - same source, different audience
def summarize(text: str, audience: str = "a busy investor", words: int = 80, case=None) -> str:
    return ask(build("a sharp editor", f"Summarize for {audience} in at most {words} words.",
                     context=shared_context(f"Source text:\n{text}\nAudience: {audience}\nMaximum words: {words}", case),
                     fmt="One paragraph, then 3 bullet takeaways"))


# 5. COMPARISON - AI scores, Python does the maths (never trust an LLM's arithmetic)
def compare(options: list, criteria: dict, case=None):
    scores = ask_json(build("a neutral analyst", "Score each option from 1 to 5 on each criterion, with a one-line reason.",
                            context=shared_context(f"Options: {options}\nCriteria: {list(criteria)}", case),
                            fmt='JSON: {"<option>": {"<criterion>": {"score": int, "why": str}}}'))
    rows = []
    for opt, crit in scores.items():
        try:
            total = sum(crit[c]["score"] * w for c, w in criteria.items()) / sum(criteria.values())
            rows.append({"option": opt, "weighted_score": round(total, 2)})
        except (KeyError, TypeError):
            continue
    table = pd.DataFrame(rows).sort_values("weighted_score", ascending=False) if rows else pd.DataFrame()
    return table, scores


# 6. ANALYSIS - numbers computed by pandas, interpretation by the AI
def analyze_frame(df: pd.DataFrame, case=None):
    stats = {"responses": len(df), "avg_rating": float(round(df.rating.mean(), 2)),
             "rating_by_segment": df.groupby("segment").rating.mean().round(2).to_dict(),
             "top_topics": df.topic.value_counts().head(3).to_dict()}
    active = case or get_case()
    stats["case"] = active.name
    insight = ask(build("a data analyst", "Explain what these numbers mean and propose 3 actions.",
                        context=shared_context(f"Numbers: {stats}", case),
                        constraints="Use only the numbers given."))
    return stats, insight


def analyze(csv_path: str, case=None):
    return analyze_frame(pd.read_csv(csv_path), case)


# 7. MODELLING - a transparent unit-economics model you can explain to a jury
def financial_model(price=9.0, cac=12.0, monthly_churn=0.06, new_per_month=40,
                    months=12, fixed_costs=600.0, gross_margin=0.8, case=None):
    customers, rows = 0.0, []
    for m in range(1, months + 1):
        customers = customers * (1 - monthly_churn) + new_per_month
        revenue = customers * price
        profit = revenue * gross_margin - fixed_costs - new_per_month * cac
        rows.append({"month": m, "customers": round(customers), "revenue": round(revenue), "profit": round(profit)})
    ltv = price * gross_margin / monthly_churn
    active = case or get_case()
    return pd.DataFrame(rows), {"LTV": round(ltv, 1), "CAC": cac, "LTV/CAC": round(ltv / cac, 2),
                                "case": active.name, "shared_context": active.text()}


# 8. PLANNING - a roadmap with owners and "done when" criteria
def plan(idea: str, weeks: int = 8, case=None):
    data = ask_json(build(MENTOR, f"Create a {weeks}-week launch plan for: {idea}",
                          context=shared_context(f"Planning focus: {idea}\nWeeks: {weeks}", case),
                          constraints="Max 3 goals per week; each has an owner role and a done-criterion.",
                          fmt='JSON: {"weeks":[{"week":int,"goals":[{"goal":str,"owner":str,"done_when":str}]}]}'))
    if isinstance(data, dict) and "weeks" in data:
        data["case"] = (case or get_case()).name
    return data


def plan_to_markdown(data: dict) -> str:
    if "weeks" not in data:
        return str(data.get("raw", data))
    lines = ["| Week | Goal | Owner | Done when |", "|---|---|---|---|"]
    for w in data["weeks"]:
        for g in w["goals"]:
            lines.append(f"| {w['week']} | {g['goal']} | {g['owner']} | {g['done_when']} |")
    return "\n".join(lines)


# 9. MULTIMEDIA - prompts for image tools (Ideogram, Canva...) + a pitch script
def media_prompts(name: str, audience: str, vibe: str = "friendly, modern", case=None) -> dict:
    brief = f"{name}, for {audience}, {vibe} style"
    return {"logo_prompt": f"Minimal vector logo for {brief}. Flat colors, white background, no text.",
            "poster_prompt": f"Launch poster for {brief}. Space for a headline at top, three-color palette.",
            "pitch_script": ask(build("a pitch coach", f"Write a 60-second pitch for {name}.",
                                      context=shared_context(f"Brand brief: {brief}", case),
                                      fmt="Hook / problem / solution / traction / ask"))}


# 10. IMPLEMENTATION - AI writes a first draft, YOU run it and review it
def implement_code(spec: str, case=None) -> str:
    code = ask(build("a senior Python developer teaching beginners", f"Write a single-file Python program: {spec}",
                     context=shared_context(f"Feature specification: {spec}", case),
                     constraints="Standard library only, comments for every step, under 80 lines.",
                     fmt="Python code only, no explanation"), max_tokens=1800)
    return re.sub(r"^```(?:python)?|```$", "", code.strip(), flags=re.M).strip()


def save_code(code: str, out_file: str = "outputs/generated_app.py") -> str:
    Path(out_file).parent.mkdir(parents=True, exist_ok=True)
    Path(out_file).write_text(code, encoding="utf-8")
    return out_file


def implement(spec: str, out_file: str = "outputs/generated_app.py", case=None) -> str:
    return save_code(implement_code(spec, case), out_file)
