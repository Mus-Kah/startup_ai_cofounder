import json
import re
import pandas as pd
from . import axes, context, i18n, llm
from .prompts import MENTOR, build

STAGE_KEYS = ["prompt", "brainstorm", "research", "extract", "summarize", "compare", "analyze", "model", "plan", "media", "implement", "api"]
STAGE_AXES = {"prompt": 0, "brainstorm": 1, "research": 2, "extract": 3, "summarize": 4, "compare": 5,
              "analyze": 6, "model": 7, "plan": 8, "media": 9, "implement": 10, "api": 11}
STAGE_TITLES = {key: f"title_{key}" for key in STAGE_KEYS}
STAGE_TITLES["prompt"] = "title_prompt"


def blank_state():
    return {"outputs": {}, "inputs": {}, "raw_inputs": {}, "status": {}}


OUTPUT_LABELS = {
    "prompt": "Prompt output",
    "brainstorm": "Brainstorming ideas",
    "research": "Research plan",
    "extract": "Extracted insights",
    "summarize": "Summary",
    "compare": "Comparison result",
    "compare_ranking": "Ranked options",
    "compare_scores": "Option scores",
    "analyze": "Analysis",
    "analyze_stats": "Computed statistics",
    "analyze_insight": "Interpretation",
    "model": "Financial model",
    "model_unit": "Unit economics",
    "plan": "Launch roadmap",
    "media": "Brand pack",
    "implement": "Generated implementation",
    "api": "API response",
}
OUTPUT_TUPLE_LABELS = {
    "compare": ["Ranked options", "Option scores"],
    "analyze": ["Computed statistics", "AI interpretation"],
    "model": ["Monthly projection", "Unit economics"],
}


def _humanize(name):
    text = re.sub(r"\s+", " ", str(name).replace("_", " ").strip())
    return text if text.isupper() else text.title()


def _clean_cell(value):
    text = "" if value is None else str(value)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _clean_text(value):
    return re.sub(r"\*\*(.*?)\*\*", r"\1", "" if value is None else str(value)).strip()


def _parse_markdown_table(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines[:-1]):
        if not (line.startswith("|") and line.endswith("|")):
            continue
        header = [cell.strip() for cell in line.strip("|").split("|")]
        separator = lines[index + 1].strip()
        if not (separator.startswith("|") and separator.endswith("|")):
            continue
        cells = [cell.strip() for cell in separator.strip("|").split("|")]
        if len(cells) != len(header) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        records = []
        cursor = index + 2
        while cursor < len(lines):
            row = lines[cursor]
            if not (row.startswith("|") and row.endswith("|")):
                break
            values = [cell.strip() for cell in row.strip("|").split("|")]
            values += [""] * (len(header) - len(values))
            records.append(dict(zip(header, values[:len(header)])))
            cursor += 1
        return records, "\n".join(lines[cursor:])
    return [], ""


def _format_records(records):
    lines = []
    for position, record in enumerate(records, 1):
        lines.append(f"ITEM {position}:")
        for name, value in record.items():
            lines.append(f"{_humanize(name)}: {_clean_cell(value)}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_mapping(data, indent=0):
    lines = []
    prefix = "  " * indent
    for name, value in data.items():
        label = _humanize(name)
        if isinstance(value, dict):
            lines.append(f"{prefix}{label}:")
            lines.extend(_format_mapping(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{label}:")
            if not value:
                lines.append(f"{prefix}  None")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}  -")
                    lines.extend(_format_mapping(item, indent + 2))
                else:
                    lines.append(f"{prefix}  - {_clean_cell(item)}")
        else:
            lines.append(f"{prefix}{label}: {_clean_cell(value)}")
    return lines


def _format_sequence(values):
    lines = []
    for position, item in enumerate(values, 1):
        if isinstance(item, dict):
            lines.append(f"ITEM {position}:")
            lines.extend(_format_mapping(item, 1))
        else:
            lines.append(f"ITEM {position}: {_clean_cell(item)}")
    return "\n".join(lines)


def _format_frame(df):
    if df is None or df.empty:
        return "NO ROWS"
    lines = [f"TABLE: {len(df)} rows; columns: {', '.join(str(column) for column in df.columns)}"]
    for position, (_, row) in enumerate(df.iterrows(), 1):
        pairs = [f"{_humanize(column)}: {_clean_cell(row[column])}" for column in df.columns]
        lines.append(f"ROW {position}: " + " | ".join(pairs))
    return "\n".join(lines)


def format_output(key, value):
    label = OUTPUT_LABELS.get(key, "")
    if isinstance(value, pd.DataFrame):
        body = _format_frame(value)
    elif isinstance(value, tuple):
        names = OUTPUT_TUPLE_LABELS.get(key)
        parts = []
        for position, part in enumerate(value):
            name = names[position] if names and position < len(names) else f"Part {position + 1}"
            parts.append(f"{name}:\n{format_output(None, part)}")
        body = "\n\n".join(parts)
    elif isinstance(value, dict):
        body = "\n".join(_format_mapping(value))
    elif isinstance(value, list):
        body = _format_sequence(value)
    else:
        text = _clean_text(value)
        records, tail = _parse_markdown_table(text)
        body = _format_records(records) if records else text
        if records and tail:
            body += "\n\nAdditional notes:\n" + _clean_text(tail)
    return f"{label}:\n{body}" if label else body


def as_text(value):
    return format_output(None, value)


def previous_output_key(key, outputs):
    index = STAGE_KEYS.index(key)
    for previous in reversed(STAGE_KEYS[:index]):
        if previous in outputs:
            return previous
    return None


def previous_output(key, outputs):
    previous = previous_output_key(key, outputs)
    return outputs[previous] if previous else None


def derive_compare(summary, case):
    raw = axes.ask_json(build("a product strategist",
                              "Turn the source into 3 concrete options and 3 weighted criteria.",
                               context=context.shared_context(f"Source to convert:\n{format_output('summarize', summary)}", case),

                              fmt='JSON: {"options":[str],"criteria":{"name":number}}'))
    options = raw.get("options") if isinstance(raw, dict) else None
    criteria = raw.get("criteria") if isinstance(raw, dict) else None
    if not isinstance(options, list) or len(options) < 2:
        options = ["Landing page waitlist", "Concierge pilot", "Campus partner"]
    if not isinstance(criteria, dict) or len(criteria) < 1:
        criteria = {"impact": 3, "cost": 2, "speed": 2}
    return {"options": [str(option) for option in options],
            "criteria": {str(name): float(weight) for name, weight in criteria.items()}}


def compare_to_frame(value):
    _, scores = value
    rows = []
    if isinstance(scores, dict):
        for option, criteria in scores.items():
            if not isinstance(criteria, dict):
                continue
            for criterion, payload in criteria.items():
                try:
                    rows.append({"rating": float(payload["score"]), "segment": str(option), "topic": str(criterion)})
                except (KeyError, TypeError):
                    continue
    if not rows:
        rows = [{"rating": 3, "segment": "baseline", "topic": "impact"}]
    return pd.DataFrame(rows)


def derive_model(analysis, case):
    stats = analysis[0] if isinstance(analysis, tuple) and isinstance(analysis[0], dict) else {}
    avg = float(stats.get("avg_rating", 3) or 3)
    price = round(max(3.0, 4.0 + avg), 2)
    cac = round(max(4.0, 16.0 - avg * 2), 2)
    churn = round(min(0.25, max(0.02, 0.16 - (avg - 3) * 0.02)), 3)
    new_per_month = max(10, int(12 + avg * 6))
    return {"price": price, "cac": cac, "monthly_churn": churn, "new_per_month": new_per_month,
            "months": 12, "fixed_costs": 600.0, "gross_margin": 0.8}


def upstream_text(key, outputs):
    previous = previous_output_key(key, outputs)
    if not previous:
        return ""
    label = OUTPUT_LABELS.get(previous, f"Axis {STAGE_AXES[previous]} output")
    return f"{label} from Axis {STAGE_AXES[previous]}:\n{format_output(previous, outputs[previous])}"


def model_to_idea(model, case):
    table, unit = model
    last = table.iloc[-1].to_dict() if isinstance(table, pd.DataFrame) and not table.empty else {}
    last_text = "\n".join(f"{_humanize(name)}: {_clean_cell(value)}" for name, value in last.items())
    return (f"{case.name}: validate {case.problem} with a launch grounded in the shared brief. "
            f"Use this structured unit economics:\n{format_output('model_unit', unit)}\n"
            f"Last modelled month:\n{last_text}.")


def plan_to_media(plan, case):
    return {"name": case.name, "audience": case.audience,
            "vibe": f"evidence-led, clear, {case.constraints}. Structured Roadmap:\n{format_output('plan', plan)[:1200]}"}


def media_to_spec(media, plan, case):
    return (f"Build a small Python app for {case.name}. Problem: {case.problem}. "
            f"Structured Brand Brief:\n{format_output('media', media)[:1000]}\n"
            f"Structured Roadmap:\n{format_output('plan', plan)[:1000]}.")


def code_to_api_body(code, case):
    return {"problem": "Prepare an integration handoff for this generated implementation:\n"
                       + format_output("implement", code)[:1200],
            "n": 3, "case_name": case.name, "case_problem": case.problem, "case_audience": case.audience,
            "case_constraints": case.constraints, "case_evidence": case.evidence}


def stage_inputs(key, outputs=None, case=None, api_base="http://127.0.0.1:8000"):
    outputs = outputs or {}
    case = case or context.get_case()
    upstream = previous_output(key, outputs)
    handoff = upstream_text(key, outputs)
    if key == "prompt":
        return {"prompt_role": MENTOR,
                "prompt_task": f"Propose 5 cheap ways to test demand for {case.problem}.",
                "prompt_context": f"{case.audience}; {case.constraints}; evidence: {case.evidence}",
                "prompt_constraints": "No invented metrics; plain language.",
                "prompt_fmt": "Numbered blocks with fields: Test, Cost, Signal of success, Main risk",
                "prompt_system": "You are a helpful, honest start-up mentor.",
                "prompt_max_tokens": 1200}
    if key == "brainstorm":
        return {"problem": f"{case.problem}\n\nStructured handoff:\n{handoff}\n\nUse the listed ideas as candidates."
                if upstream else case.problem, "n": 8}
    if key == "research":
        return {"idea": f"Validate this structured handoff:\n{handoff}" if upstream else case.problem}
    if key == "extract":
        return {"text": f"Source material from the previous axis:\n{handoff}" if upstream else case.evidence}
    if key == "summarize":
        return {"text": f"Source material from the previous axis:\n{handoff}" if upstream else case.evidence,
                "audience": case.audience, "words": 80}
    if key == "compare":
        return derive_compare(upstream, case) if upstream else {"options": [case.name], "criteria": {"impact": 1}}
    if key == "analyze":
        return {"df": compare_to_frame(upstream) if upstream else pd.DataFrame()}
    if key == "model":
        return derive_model(upstream, case) if upstream else {"price": 9.0, "cac": 12.0, "monthly_churn": 0.06,
                                                               "new_per_month": 40, "months": 12,
                                                               "fixed_costs": 600.0, "gross_margin": 0.8}
    if key == "plan":
        return {"idea": model_to_idea(upstream, case) if upstream else case.problem, "weeks": 8}
    if key == "media":
        return plan_to_media(upstream, case) if upstream else {"name": case.name, "audience": case.audience,
                                                                "vibe": "friendly, modern"}
    if key == "implement":
        plan = outputs.get("plan")
        return {"spec": media_to_spec(upstream, plan, case) if upstream else case.problem}
    if key == "api":
        return {"base": api_base, "endpoint": "POST /brainstorm", "body": code_to_api_body(upstream, case) if upstream else {}}
    raise KeyError(key)


def run_stage(key, inputs, case=None, api_caller=None):
    case = case or context.get_case()
    if key == "prompt":
        prompt = build(inputs["prompt_role"], inputs["prompt_task"],
                       context.shared_context(inputs["prompt_context"], case),
                       inputs["prompt_constraints"], inputs["prompt_fmt"])
        return llm.ask(prompt, system=inputs["prompt_system"], max_tokens=inputs["prompt_max_tokens"])
    if key == "brainstorm":
        return axes.brainstorm(inputs["problem"], inputs["n"], case=case)
    if key == "research":
        return axes.research_plan(inputs["idea"], case=case)
    if key == "extract":
        return axes.extract(inputs["text"], case=case)
    if key == "summarize":
        return axes.summarize(inputs["text"], inputs["audience"], inputs["words"], case=case)
    if key == "compare":
        return axes.compare(inputs["options"], inputs["criteria"], case=case)
    if key == "analyze":
        return axes.analyze_frame(inputs["df"], case=case)
    if key == "model":
        return axes.financial_model(inputs["price"], inputs["cac"], inputs["monthly_churn"],
                                    inputs["new_per_month"], inputs["months"], inputs["fixed_costs"],
                                    inputs["gross_margin"], case=case)
    if key == "plan":
        return axes.plan(inputs["idea"], inputs["weeks"], case=case)
    if key == "media":
        return axes.media_prompts(inputs["name"], inputs["audience"], inputs["vibe"], case=case)
    if key == "implement":
        return axes.implement_code(inputs["spec"], case=case)
    if key == "api":
        if api_caller is None:
            return {"endpoint": inputs["endpoint"], "body": inputs["body"], "status": "API caller not configured"}
        return api_caller(inputs["base"], inputs["endpoint"], json.dumps(inputs["body"]))
    raise KeyError(key)


def run_all(state=None, api_caller=None, stop_on_error=True):
    state = state or blank_state()
    state.setdefault("outputs", {})
    state.setdefault("inputs", {})
    state.setdefault("raw_inputs", {})
    state.setdefault("status", {})
    for key in STAGE_KEYS:
        try:
            inputs = stage_inputs(key, state["outputs"])
            state["inputs"][key] = {k: f"<DataFrame {v.shape}>" if isinstance(v, pd.DataFrame) else v
                                    for k, v in inputs.items()}
            state["raw_inputs"][key] = inputs
            state["outputs"][key] = run_stage(key, inputs, api_caller=api_caller)
            state["status"][key] = "ok"
        except Exception as exc:
            state["status"][key] = str(exc)
            if stop_on_error:
                break
    return state
