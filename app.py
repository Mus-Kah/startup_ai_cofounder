"""Browser GUI for the lab:  python app.py"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx(suppress_warning=True) is not None
    except Exception:
        return False


if __name__ == "__main__" and not os.environ.get("AI_STARTUP_LAB_GUI") and not in_streamlit():
    env = os.environ.copy()
    env["AI_STARTUP_LAB_GUI"] = "1"
    command = [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()), *sys.argv[1:]]
    raise SystemExit(subprocess.call(command, env=env))

import pandas as pd
import streamlit as st

from src import axes, cli, context, i18n, llm, pipeline
from src.prompts import MENTOR, build

ROOT = Path(__file__).resolve().parent
SAMPLE_INTERVIEW = ROOT / "data/interview.txt"
SAMPLE_FEEDBACK = ROOT / "data/feedback.csv"
OUTPUT = ROOT / "outputs/generated_app.py"
CASE = cli.CASE
DEFAULT_API_BASE = "http://127.0.0.1:8000"
SAMPLE_INTERVIEW_TEXT = SAMPLE_INTERVIEW.read_text(encoding="utf-8") if SAMPLE_INTERVIEW.exists() else ""
MENTOR_SYSTEM = "You are a helpful, honest start-up mentor."
RTL_CSS = """
<style>
[data-testid="stAppViewContainer"], [data-testid="stSidebar"] { direction: rtl; }
textarea, input { direction: rtl; text-align: right; }
</style>
"""

st.set_page_config(page_title=i18n.tr("app_title"), layout="wide")

DEFAULTS = {
    "prompt_role": MENTOR,
    "prompt_task": f"Propose 5 cheap ways to test demand for {context.DEFAULT_CASE.problem}.",
    "prompt_context": f"{context.DEFAULT_CASE.audience}; {context.DEFAULT_CASE.constraints}; evidence: {context.DEFAULT_CASE.evidence}",
    "prompt_constraints": "No invented metrics; plain language.",
    "prompt_fmt": "Table: test | cost | signal of success",
    "prompt_system": MENTOR_SYSTEM,
    "prompt_max_tokens": 1200,
    "brainstorm_problem": context.DEFAULT_CASE.problem,
    "brainstorm_n": 8,
    "research_idea": context.DEFAULT_CASE.problem,
    "extract_source": "paste",
    "summarize_source": "paste",
    "summarize_audience": context.DEFAULT_CASE.audience,
    "summarize_words": 80,
    "compare_options": "",
    "compare_criteria": "",
    "analyze_source": "upstream",
    "model_price": 9.0,
    "model_cac": 12.0,
    "model_churn": 0.06,
    "model_new": 40,
    "model_months": 12,
    "model_fixed": 600.0,
    "model_margin": 0.8,
    "plan_idea": context.DEFAULT_CASE.problem,
    "plan_weeks": 8,
    "media_name": context.DEFAULT_CASE.name,
    "media_audience": context.DEFAULT_CASE.audience,
    "media_vibe": "friendly, modern",
    "implement_spec": f"Build a first prototype for {context.DEFAULT_CASE.name}: {context.DEFAULT_CASE.problem}.",
    "api_base": DEFAULT_API_BASE,
    "api_endpoint": "GET /health",
    "api_body": "{}",
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
for key, value in context.DEFAULT_CASE.dict().items():
    st.session_state.setdefault(f"case_{key}", value)
st.session_state.setdefault("app_language", i18n.get_language())


def language_selector():
    names = list(i18n.LANGUAGES)
    current = i18n.get_language()
    selected = st.sidebar.selectbox(i18n.tr("language"), names, index=names.index(current),
                                    key="app_language", format_func=i18n.label)
    if selected != current:
        i18n.set_language(selected)
        st.rerun()
    if i18n.direction() == "rtl":
        st.markdown(RTL_CSS, unsafe_allow_html=True)


def case_editor():
    with st.sidebar.expander(i18n.tr("shared_case"), expanded=False):
        active = context.CaseBrief(
            name=st.text_input(i18n.tr("case_name"), key="case_name"),
            problem=st.text_area(i18n.tr("problem"), height=80, key="case_problem"),
            audience=st.text_input(i18n.tr("target_user"), key="case_audience"),
            constraints=st.text_area(i18n.tr("constraints"), height=60, key="case_constraints"),
            evidence=st.text_area(i18n.tr("evidence"), height=60, key="case_evidence"))
        context.set_case(active)
        st.code(active.text())
        if st.button(i18n.tr("apply_to_task_fields"), key="case_apply"):
            st.session_state["brainstorm_problem"] = active.problem
            st.session_state["research_idea"] = active.problem
            st.session_state["plan_idea"] = active.problem
            st.session_state["media_name"] = active.name
            st.session_state["media_audience"] = active.audience
            st.session_state["prompt_context"] = i18n.tr("case_context_template", audience=active.audience,
                                                         constraints=active.constraints, evidence=active.evidence)
            st.rerun()
        if st.button(i18n.tr("reset_case"), key="case_reset"):
            for key, value in context.DEFAULT_CASE.dict().items():
                st.session_state[f"case_{key}"] = value
            st.rerun()


def show_mode():
    names = list(llm.PROVIDERS)
    current = llm.current_provider()
    selected = st.sidebar.selectbox(i18n.tr("llm_api"), names, index=names.index(current), key="llm_provider",
                                    format_func=lambda name: llm.PROVIDERS[name]["label"])
    if selected != current:
        llm.set_provider(selected)
        st.rerun()
    spec = llm.PROVIDERS[selected]
    if llm.configured():
        st.sidebar.success(f"{i18n.tr('live')}: {spec['label']} / {llm.current_model()}")
    else:
        st.sidebar.warning(f"{i18n.tr('mock')}: set {spec['key_env']} in .env for live {spec['label']} answers")
    st.sidebar.caption(i18n.tr("api_used_all"))
    st.sidebar.caption(f"{i18n.tr('runs_saved')}: {len(st.session_state.get('history', []))}")


def preview(values):
    clipped = {}
    for key, value in values.items():
        if isinstance(value, str) and len(value) > 700:
            clipped[key] = value[:700] + "..."
        elif isinstance(value, pd.DataFrame):
            clipped[key] = {"rows": len(value), "columns": list(value.columns)}
        else:
            clipped[key] = value
    return json.dumps(clipped, indent=2, default=str)


def result_text(value):
    if isinstance(value, pd.DataFrame):
        return value.to_string(index=False) if not value.empty else "(empty table)"
    if isinstance(value, tuple):
        return "\n\n".join(result_text(part) for part in value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, default=str)
    return str(value)


def remember(task, key, inputs, value, seconds):
    safe_inputs = {k: f"<{type(v).__name__}>" if isinstance(v, pd.DataFrame) else v for k, v in inputs.items()}
    active_case = context.get_case()
    upstream = pipeline.previous_output_key(key, outputs_for_presets()) if key in pipeline.STAGE_KEYS else None
    entry = {"task": task, "key": key, "inputs": safe_inputs, "value": value, "text": result_text(value),
             "case": active_case.dict(), "case_text": active_case.text(), "language": i18n.get_language(),
             "upstream": upstream, "seconds": round(seconds, 2), "at": datetime.now().strftime("%H:%M:%S")}
    history = st.session_state.setdefault("history", [])
    history.insert(0, entry)
    del history[20:]
    st.session_state.setdefault("results", {})[key] = entry


def outputs_for_presets():
    outputs = dict(flow_state()["outputs"])
    results = st.session_state.get("results", {})
    for key in pipeline.STAGE_KEYS:
        for result_key in (key, f"flow_{key}"):
            entry = results.get(result_key)
            if entry and "value" in entry:
                outputs[key] = entry["value"]
    return outputs


def upstream_signature(key, outputs=None, case=None):
    if key not in pipeline.STAGE_KEYS:
        return ""
    outputs = outputs if outputs is not None else outputs_for_presets()
    case = case or context.get_case()
    upstream = pipeline.previous_output_key(key, outputs)
    source = pipeline.as_text(outputs[upstream]) if upstream else json.dumps(case.dict(), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(f"{upstream or 'case'}:{source}".encode("utf-8")).hexdigest()[:16]


def session_values(key, inputs):
    if key == "prompt":
        return dict(inputs)
    if key == "brainstorm":
        return {"brainstorm_problem": inputs["problem"], "brainstorm_n": inputs["n"]}
    if key == "research":
        return {"research_idea": inputs["idea"]}
    if key == "extract":
        return {"extract_source": "paste", "extract_text": inputs["text"]}
    if key == "summarize":
        return {"summarize_source": "paste", "summarize_text": inputs["text"],
                "summarize_audience": inputs["audience"], "summarize_words": inputs["words"]}
    if key == "compare":
        options = "\n".join(str(option) for option in inputs["options"])
        criteria = "\n".join(f"{name}: {weight}" for name, weight in inputs["criteria"].items())
        return {"compare_options": options, "compare_criteria": criteria}
    if key == "analyze":
        return {"analyze_source": "upstream", "analyze_upstream_df": inputs["df"]}
    if key == "model":
        return {"model_price": inputs["price"], "model_cac": inputs["cac"], "model_churn": inputs["monthly_churn"],
                "model_new": inputs["new_per_month"], "model_months": inputs["months"],
                "model_fixed": inputs["fixed_costs"], "model_margin": inputs["gross_margin"]}
    if key == "plan":
        return {"plan_idea": inputs["idea"], "plan_weeks": inputs["weeks"]}
    if key == "media":
        return {"media_name": inputs["name"], "media_audience": inputs["audience"], "media_vibe": inputs["vibe"]}
    if key == "implement":
        return {"implement_spec": inputs["spec"]}
    if key == "api":
        return {"api_base": inputs["base"], "api_endpoint": inputs["endpoint"],
                "api_body": json.dumps(inputs["body"], indent=2, ensure_ascii=False)}
    return {}


def apply_session_values(key, inputs):
    for name, value in session_values(key, inputs).items():
        st.session_state[name] = value


def stage_preset(key):
    state = flow_state()
    outputs = outputs_for_presets()
    signature = upstream_signature(key, outputs, context.get_case())
    cached = state.get("raw_inputs", {}).get(key)
    if cached and cached.get("signature") == signature:
        values = cached["values"]
    else:
        values = pipeline.stage_inputs(key, outputs, context.get_case())
        state.setdefault("raw_inputs", {})[key] = {"signature": signature, "values": values}
    upstream = pipeline.previous_output_key(key, outputs)
    label = i18n.tr("preset_upstream", axis=pipeline.STAGE_AXES[upstream]) if upstream else i18n.tr("preset_case_brief")
    return label, values


def sync_stage_inputs(key):
    if key not in pipeline.STAGE_KEYS:
        return
    label, values = stage_preset(key)
    signature = upstream_signature(key)
    applied_key = f"upstream_applied_{key}"
    if st.session_state.get(applied_key) != signature:
        apply_session_values(key, values)
        st.session_state[f"{key}_preset"] = label
        st.session_state[applied_key] = signature
        st.rerun()


def run_task(key, title, function, inputs):
    started = time.perf_counter()
    try:
        with st.spinner(i18n.tr("running", title=title)):
            value = function()
        seconds = time.perf_counter() - started
        remember(title, key, inputs, value, seconds)
        st.session_state.setdefault("status", {})[key] = i18n.tr("completed_in", seconds=seconds,
                                                                 clock=datetime.now().strftime("%H:%M:%S"))
        st.session_state.setdefault("status_ok", {})[key] = True
    except Exception as exc:
        st.session_state.setdefault("status", {})[key] = f"{i18n.tr('failed')}: {exc}"
        st.session_state.setdefault("status_ok", {})[key] = False
        st.error(f"{title} {i18n.tr('failed')}: {exc}")


def show_json(data):
    if isinstance(data, dict) and "raw" in data:
        st.warning(i18n.tr("structured_output_failed"))
        st.code(str(data["raw"]))
    else:
        st.json(data)


def render_value(value):
    if isinstance(value, pd.DataFrame):
        if value.empty:
            st.warning(i18n.tr("no_rows"))
        else:
            st.dataframe(value)
    elif isinstance(value, tuple):
        for part in value:
            render_value(part)
    elif isinstance(value, str):
        st.markdown(value)
    else:
        show_json(value)


def render_checks(value):
    for label, passed, detail in value:
        col1, col2 = st.columns([3, 1])
        col1.write(label)
        if passed:
            col2.success(i18n.tr("ok"))
        else:
            col2.error(i18n.tr("missing"))
        if detail:
            st.caption(detail.strip())


def render_compare(value):
    table, scores = value
    if table.empty:
        st.warning(i18n.tr("no_scores"))
    else:
        st.dataframe(table)
    st.subheader(i18n.tr("raw_scores"))
    show_json(scores)


def render_model(value):
    table, unit = value
    for label, number in unit.items():
        if label in ("case", "shared_context"):
            continue
        st.metric(label, number)
    st.dataframe(table)
    try:
        st.line_chart(table.set_index("month")[["customers", "revenue", "profit"]])
    except Exception as exc:
        st.warning(f"{i18n.tr('chart_unavailable')}: {exc}")
    st.download_button(i18n.tr("download_model_csv"), table.to_csv(index=False), file_name="model.csv", mime="text/csv")


def render_plan(value):
    markdown = axes.plan_to_markdown(value)
    st.markdown(markdown)
    if isinstance(value, dict) and "weeks" not in value:
        show_json(value)
    st.download_button(i18n.tr("download_roadmap"), markdown, file_name="roadmap.md", mime="text/markdown")


def render_media(value):
    labels = {"logo_prompt": "media_logo_prompt", "poster_prompt": "media_poster_prompt", "pitch_script": "media_pitch_script"}
    for key, text in value.items():
        with st.expander(i18n.tr(labels.get(key, key)), expanded=key == "pitch_script"):
            st.markdown(str(text))


def render_implement(value):
    st.code(value, language="python")
    out_file = st.text_input(i18n.tr("save_as"), value=str(OUTPUT), key="implement_out_file")
    if st.button(i18n.tr("save_draft"), key="implement_save"):
        try:
            saved = axes.save_code(value, out_file)
            st.success(i18n.tr("saved_to", path=saved))
        except Exception as exc:
            st.error(f"{i18n.tr('could_not_save')}: {exc}")


def focus_result(key):
    safe_key = re.sub(r"[^A-Za-z0-9_]", "_", key)
    anchor = f"result-focus-{safe_key}"
    st.html(f'''<div id="{anchor}" tabindex="-1"></div>
<script>
(function () {{
  var target = document.getElementById("{anchor}");
  function move() {{
    if (!target) return;
    target.scrollIntoView({{ behavior: "smooth", block: "start" }});
    target.focus({{ preventScroll: true }});
  }}
  window.requestAnimationFrame(move);
  window.setTimeout(move, 120);
}})();
</script>''', unsafe_allow_javascript=True)


def render_result(key, renderer=None):
    status = st.session_state.get("status", {}).get(key, "")
    status_ok = st.session_state.get("status_ok", {})
    if status:
        if key in status_ok and not status_ok[key]:
            st.error(status)
        else:
            st.success(status)
    entry = st.session_state.get("results", {}).get(key)
    if not entry:
        st.info(i18n.tr("run_task_to_see"))
        return
    upstream = entry.get("upstream")
    if upstream:
        st.caption(f"{i18n.tr('used_output_from')}: {i18n.tr(pipeline.STAGE_TITLES[upstream])}")
    with st.expander(i18n.tr("inputs_used")):
        st.code(json.dumps(entry["inputs"], indent=2, default=str))
    with st.expander(i18n.tr("shared_case_used")):
        st.code(entry.get("case_text", context.get_case().text()))
    if renderer:
        renderer(entry["value"])
    else:
        render_value(entry["value"])


def task_page(key, title, description, inputs_fn, preview_fn, runner, renderer=None):
    st.header(title)
    st.caption(description)
    st.caption(f"{i18n.tr('shared_case_label')}: {context.get_case().name} — {context.get_case().problem}")
    sync_stage_inputs(key)
    preset_label = stage_preset(key)[0] if key in pipeline.STAGE_KEYS else i18n.tr("custom")
    left, right = st.columns([1, 1.35])
    with left:
        with st.container(border=True):
            st.subheader(i18n.tr("inputs"))
            if key in pipeline.STAGE_KEYS:
                chosen = st.selectbox(i18n.tr("preset"), ["Custom", preset_label], key=f"{key}_preset")
                if st.button(i18n.tr("reload_upstream"), key=f"{key}_load", disabled=chosen == "Custom"):
                    apply_session_values(key, stage_preset(key)[1])
                    st.session_state[f"{key}_preset"] = preset_label
                    st.rerun()
            inputs = inputs_fn()
            st.caption(i18n.tr("live_preview"))
            st.code(preview_fn(inputs))
            status_ok = st.session_state.get("status_ok", {})
            label = i18n.tr("retry") if status_ok.get(key) is False else i18n.tr("run_again") if key in st.session_state.get("results", {}) else i18n.tr("run")
            if st.button(label, key=f"{key}_run"):
                st.session_state[f"focus_result_{key}"] = True
                run_task(key, title, lambda: runner(inputs), inputs)
    with right:
        if st.session_state.get(f"focus_result_{key}"):
            st.session_state[f"focus_result_{key}"] = False
            focus_result(key)
        with st.container(border=True):
            st.subheader(i18n.tr("result"))
            render_result(key, renderer)


def source_inputs(key):
    source = st.radio(i18n.tr("source"), ["sample", "paste", "upload"],
                      format_func=lambda value: i18n.tr(f"source_{value}"), horizontal=True, key=f"{key}_source")
    if source == "sample":
        return SAMPLE_INTERVIEW_TEXT
    if source == "paste":
        return st.text_area(i18n.tr("text"), height=180, key=f"{key}_text")
    uploaded = st.file_uploader(i18n.tr("interview_text"), type=["txt"], key=f"{key}_file")
    return uploaded.getvalue().decode("utf-8") if uploaded else ""


def parse_compare(values):
    options = [line.strip() for line in values["options"].splitlines() if line.strip()]
    criteria = {}
    for line in values["criteria"].splitlines():
        if not line.strip():
            continue
        name, weight = line.split(":", 1)
        criteria[name.strip()] = float(weight)
    if not options or not criteria:
        raise ValueError(i18n.tr("add_option_criterion"))
    if sum(criteria.values()) <= 0:
        raise ValueError(i18n.tr("total_weight_positive"))
    return options, criteria


def local_api_response(endpoint, body):
    payload = json.loads(body) if body else {}
    active = context.get_case().dict()
    base = active if active.get("name") else context.DEFAULT_CASE.dict()
    case = {key: payload.get(key) or base.get(key, "") for key in base}
    return {"status": "local_fallback", "mode": "local_fallback", "endpoint": endpoint,
            "note": i18n.tr("api_offline"), "received": payload, "case": case}


def api_request(base, endpoint, body):
    method, path = endpoint.split(" ", 1)
    url = base.rstrip("/") + path
    if method == "GET":
        request = urllib.request.Request(url)
    else:
        request = urllib.request.Request(url, data=json.dumps(json.loads(body)).encode("utf-8"),
                                         headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError):
        return local_api_response(endpoint, body)


def prompt_inputs():
    return {"role": st.text_input(i18n.tr("role"), key="prompt_role"),
            "task": st.text_area(i18n.tr("task_label"), key="prompt_task"),
            "context": st.text_area(i18n.tr("context"), key="prompt_context"),
            "constraints": st.text_area(i18n.tr("constraints"), key="prompt_constraints"),
            "fmt": st.text_area(i18n.tr("output_format"), key="prompt_fmt"),
            "system": st.text_input(i18n.tr("system"), key="prompt_system"),
            "max_tokens": st.slider(i18n.tr("max_tokens"), 300, 3000, step=100, key="prompt_max_tokens")}


def prompt_preview(values):
    return build(values["role"], values["task"],
                 context.shared_context(values["context"]), values["constraints"], values["fmt"])


def brainstorm_inputs():
    return {"problem": st.text_area(i18n.tr("problem"), key="brainstorm_problem"),
            "n": st.slider(i18n.tr("number_of_ideas"), 1, 10, key="brainstorm_n")}


def research_inputs():
    return {"idea": st.text_area(i18n.tr("idea_to_validate"), key="research_idea")}


def extract_inputs():
    return {"text": source_inputs("extract")}


def summarize_inputs():
    text = source_inputs("summarize")
    return {"text": text, "audience": st.text_input(i18n.tr("audience"), key="summarize_audience"),
            "words": st.slider(i18n.tr("maximum_words"), 20, 300, step=10, key="summarize_words")}


def compare_inputs():
    return {"options": st.text_area(i18n.tr("options_one_per_line"), key="compare_options"),
            "criteria": st.text_area(i18n.tr("criteria_one_per_line"), key="compare_criteria")}


def analyze_inputs():
    source = st.radio(i18n.tr("source"), ["upstream", "sample", "upload"], key="analyze_source",
                      format_func=lambda value: i18n.tr("source_upstream") if value == "upstream"
                      else i18n.tr("use_sample_feedback") if value == "sample" else i18n.tr("feedback_csv"))
    df = None
    if source == "upstream":
        df = st.session_state.get("analyze_upstream_df")
    elif source == "sample":
        if SAMPLE_FEEDBACK.exists():
            df = pd.read_csv(SAMPLE_FEEDBACK)
    else:
        uploaded = st.file_uploader(i18n.tr("feedback_csv"), type=["csv"], key="analyze_file")
        if uploaded:
            df = pd.read_csv(uploaded)
    if df is not None:
        st.dataframe(df.head())
    return {"df": df, "rows": len(df) if df is not None else 0, "source": source}


def analyze_preview(values):
    if values["df"] is None:
        return "{}"
    return json.dumps({"rows": values["rows"], "columns": list(values["df"].columns)}, indent=2)


def model_inputs():
    col1, col2 = st.columns(2)
    with col1:
        price = st.number_input(i18n.tr("price_per_customer"), min_value=0.0, step=1.0, key="model_price")
        cac = st.number_input(i18n.tr("customer_acquisition_cost"), min_value=0.0, step=1.0, key="model_cac")
        churn = st.number_input(i18n.tr("monthly_churn"), min_value=0.001, max_value=0.99, step=0.01, key="model_churn")
        new_per_month = st.number_input(i18n.tr("new_customers_per_month"), min_value=0, step=5, key="model_new")
    with col2:
        months = st.slider(i18n.tr("months"), 1, 36, key="model_months")
        fixed_costs = st.number_input(i18n.tr("fixed_costs_per_month"), min_value=0.0, step=50.0, key="model_fixed")
        gross_margin = st.slider(i18n.tr("gross_margin"), 0.0, 1.0, step=0.05, key="model_margin")
    return {"price": price, "cac": cac, "churn": churn, "new_per_month": new_per_month,
            "months": months, "fixed_costs": fixed_costs, "gross_margin": gross_margin}


def plan_inputs():
    return {"idea": st.text_area(i18n.tr("idea"), key="plan_idea"),
            "weeks": st.slider(i18n.tr("weeks"), 1, 12, key="plan_weeks")}


def media_inputs():
    return {"name": st.text_input(i18n.tr("product_name"), key="media_name"),
            "audience": st.text_input(i18n.tr("audience"), key="media_audience"),
            "vibe": st.text_input(i18n.tr("vibe"), key="media_vibe")}


def implement_inputs():
    return {"spec": st.text_area(i18n.tr("spec"), key="implement_spec")}


def api_inputs():
    return {"base": st.text_input(i18n.tr("base_url"), key="api_base"),
            "endpoint": st.selectbox(i18n.tr("endpoint"), ["GET /health", "POST /brainstorm", "POST /summarize", "POST /model"], key="api_endpoint"),
            "body": st.text_area(i18n.tr("json_body"), height=180, key="api_body")}


def run_extract(values):
    if not values["text"].strip():
        raise ValueError(i18n.tr("add_text_first"))
    return axes.extract(values["text"])


def run_summarize(values):
    if not values["text"].strip():
        raise ValueError(i18n.tr("add_summarize_text"))
    return axes.summarize(values["text"], values["audience"], values["words"])


def run_analyze(values):
    df = values["df"]
    if df is None:
        raise ValueError(i18n.tr("choose_csv"))
    missing = {"rating", "segment", "topic"} - set(df.columns)
    if missing:
        raise ValueError(f"{i18n.tr('csv_needs')}: {', '.join(sorted(missing))}")
    return axes.analyze_frame(df)


def flow_state():
    st.session_state.setdefault("flow_state", pipeline.blank_state())
    return st.session_state["flow_state"]


def flow_input_preview(inputs):
    return {key: f"<DataFrame {value.shape}>" if isinstance(value, pd.DataFrame) else value
            for key, value in inputs.items()}


def parse_flow_inputs(key, edited, original):
    data = json.loads(edited)
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    if key == "analyze":
        data["df"] = original["df"]
    return data


def run_flow_stage(key, inputs):
    state = flow_state()
    started = time.perf_counter()
    title = i18n.tr(pipeline.STAGE_TITLES[key])
    try:
        with st.spinner(i18n.tr("running", title=title)):
            value = pipeline.run_stage(key, inputs, api_caller=api_request)
        seconds = time.perf_counter() - started
        state["outputs"][key] = value
        state["inputs"][key] = flow_input_preview(inputs)
        state.setdefault("raw_inputs", {})[key] = {
            "signature": upstream_signature(key, state["outputs"], context.get_case()), "values": inputs}
        state["status"][key] = "ok"
        remember(title, f"flow_{key}", inputs, value, seconds)
    except Exception as exc:
        state["status"][key] = str(exc)
        st.error(f"{title} {i18n.tr('failed')}: {exc}")


def render_flow_value(key, value):
    renderers = {"compare": render_compare, "model": render_model, "plan": render_plan,
                 "media": render_media, "implement": render_implement}
    if key in renderers:
        renderers[key](value)
    else:
        render_value(value)


def page_workflow():
    st.header(i18n.tr("title_flow"))
    st.caption(i18n.tr("desc_flow"))
    st.caption(f"{i18n.tr('shared_case_label')}: {context.get_case().name} — {context.get_case().problem}")
    state = flow_state()
    outputs = state["outputs"]
    completed = [key for key in pipeline.STAGE_KEYS if key in outputs]
    next_key = next((key for key in pipeline.STAGE_KEYS if key not in outputs), None)
    failed = [key for key, status in state["status"].items() if status != "ok"]

    top1, top2, top3 = st.columns([1, 1, 1])
    with top1:
        st.metric(i18n.tr("chain_status"), f"{len(completed)}/12")
    with top2:
        stop_on_error = st.checkbox(i18n.tr("stop_on_error"), value=True, key="flow_stop_on_error")
    with top3:
        if st.button(i18n.tr("reset_chain"), key="flow_reset"):
            st.session_state["flow_state"] = pipeline.blank_state()
            for name in list(st.session_state):
                if name.startswith("upstream_applied_"):
                    del st.session_state[name]
            st.rerun()

    if len(completed) == len(pipeline.STAGE_KEYS):
        st.success(i18n.tr("chain_done"))
    elif failed:
        st.warning(i18n.tr("chain_stopped"))

    if next_key:
        st.subheader(f"{i18n.tr('current_axis')}: {i18n.tr(pipeline.STAGE_TITLES[next_key])}")
        st.caption(i18n.tr("chain_hint"))
        preset_label, original_inputs = stage_preset(next_key)
        st.caption(f"{i18n.tr('preset')}: {preset_label}")
        editable = st.text_area(i18n.tr("edit_next_inputs"),
                                value=json.dumps(flow_input_preview(original_inputs), indent=2, ensure_ascii=False),
                                height=220, key=f"flow_edit_{next_key}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(i18n.tr("run_next"), key="flow_run_next"):
                st.session_state["focus_result_flow"] = True
                try:
                    run_flow_stage(next_key, parse_flow_inputs(next_key, editable, original_inputs))
                except Exception as exc:
                    st.error(str(exc))
                st.rerun()
        with col2:
            if st.button(i18n.tr("run_all"), key="flow_run_all"):
                st.session_state["focus_result_flow"] = True
                progress = st.progress(0)
                for key in pipeline.STAGE_KEYS:
                    if key in outputs:
                        continue
                    try:
                        inputs = stage_preset(key)[1]
                        run_flow_stage(key, inputs)
                    except Exception as exc:
                        st.error(str(exc))
                        if stop_on_error:
                            break
                    progress.progress((pipeline.STAGE_KEYS.index(key) + 1) / len(pipeline.STAGE_KEYS))
                st.rerun()

    if st.session_state.get("focus_result_flow"):
        st.session_state["focus_result_flow"] = False
        focus_result("flow")
    st.subheader(i18n.tr("chain_outputs"))
    for key in pipeline.STAGE_KEYS:
        title = i18n.tr(pipeline.STAGE_TITLES[key])
        expanded = key == next_key
        with st.expander(f"Axis {pipeline.STAGE_AXES[key]} — {title}", expanded=expanded):
            upstream = pipeline.previous_output_key(key, outputs_for_presets())
            if upstream:
                st.caption(f"{i18n.tr('used_output_from')}: {i18n.tr(pipeline.STAGE_TITLES[upstream])}")
            if key in state["inputs"]:
                with st.expander(i18n.tr("view_input")):
                    st.code(json.dumps(state["inputs"][key], indent=2, ensure_ascii=False, default=str))
            if key in outputs:
                with st.expander(i18n.tr("view_output"), expanded=expanded):
                    render_flow_value(key, outputs[key])
            else:
                st.info(i18n.tr("no_output_yet"))


def page_status():
    task_page("status", i18n.tr("title_status"), i18n.tr("desc_status"),
              lambda: {}, lambda values: "{}", lambda values: cli.checks(), render_checks)


def page_prompt():
    task_page("prompt", i18n.tr("title_prompt"), i18n.tr("desc_prompt"),
              prompt_inputs, prompt_preview,
              lambda values: llm.ask(prompt_preview(values), system=values["system"], max_tokens=values["max_tokens"]))


def page_brainstorm():
    task_page("brainstorm", i18n.tr("title_brainstorm"), i18n.tr("desc_brainstorm"),
              brainstorm_inputs, preview, lambda values: axes.brainstorm(values["problem"], values["n"]))


def page_research():
    task_page("research", i18n.tr("title_research"), i18n.tr("desc_research"),
              research_inputs, preview, lambda values: axes.research_plan(values["idea"]))


def page_extract():
    task_page("extract", i18n.tr("title_extract"), i18n.tr("desc_extract"), extract_inputs, preview, run_extract)


def page_summarize():
    task_page("summarize", i18n.tr("title_summarize"), i18n.tr("desc_summarize"),
              summarize_inputs, preview, run_summarize)


def page_compare():
    task_page("compare", i18n.tr("title_compare"), i18n.tr("desc_compare"),
              compare_inputs, preview, lambda values: axes.compare(*parse_compare(values)), render_compare)


def page_analyze():
    task_page("analyze", i18n.tr("title_analyze"), i18n.tr("desc_analyze"),
              analyze_inputs, analyze_preview, run_analyze)


def page_model():
    task_page("model", i18n.tr("title_model"), i18n.tr("desc_model"),
              model_inputs, preview,
              lambda values: axes.financial_model(values["price"], values["cac"], values["churn"],
                                                  values["new_per_month"], values["months"],
                                                  values["fixed_costs"], values["gross_margin"]), render_model)


def page_plan():
    task_page("plan", i18n.tr("title_plan"), i18n.tr("desc_plan"),
              plan_inputs, preview, lambda values: axes.plan(values["idea"], values["weeks"]), render_plan)


def page_media():
    task_page("media", i18n.tr("title_media"), i18n.tr("desc_media"),
              media_inputs, preview,
              lambda values: axes.media_prompts(values["name"], values["audience"], values["vibe"]), render_media)


def page_implement():
    task_page("implement", i18n.tr("title_implement"), i18n.tr("desc_implement"),
              implement_inputs, preview, lambda values: axes.implement_code(values["spec"]), render_implement)


def page_api():
    task_page("api", i18n.tr("title_api"), i18n.tr("desc_api"),
              api_inputs, preview, lambda values: api_request(values["base"], values["endpoint"], values["body"]))


def page_history():
    st.header(i18n.tr("history_title"))
    st.caption(i18n.tr("history_caption"))
    entries = st.session_state.get("history", [])
    if not entries:
        st.info(i18n.tr("no_runs"))
        return
    labels = [f"{entry['at']} | {entry['task']} | {entry['seconds']}s" for entry in entries]
    col1, col2 = st.columns(2)
    with col1:
        left = st.selectbox(i18n.tr("run_a"), range(len(entries)), format_func=lambda i: labels[i])
    with col2:
        right = st.selectbox(i18n.tr("run_b"), range(len(entries)), format_func=lambda i: labels[i],
                             index=min(1, len(entries) - 1))
    out1, out2 = st.columns(2)
    with out1:
        st.subheader("A")
        st.code(entries[left]["text"])
        with st.expander(i18n.tr("shared_case_a")):
            st.code(entries[left].get("case_text", ""))
        with st.expander(i18n.tr("inputs_a")):
            st.code(json.dumps(entries[left]["inputs"], indent=2, default=str))
    with out2:
        st.subheader("B")
        st.code(entries[right]["text"])
        with st.expander(i18n.tr("shared_case_b")):
            st.code(entries[right].get("case_text", ""))
        with st.expander(i18n.tr("inputs_b")):
            st.code(json.dumps(entries[right]["inputs"], indent=2, default=str))
    if st.button(i18n.tr("clear_history")):
        st.session_state.history = []
        st.rerun()


PAGE_KEYS = [("flow", page_workflow), ("status", page_status), ("prompt", page_prompt),
             ("brainstorm", page_brainstorm), ("research", page_research), ("extract", page_extract),
             ("summarize", page_summarize), ("compare", page_compare), ("analyze", page_analyze),
             ("model", page_model), ("plan", page_plan), ("media", page_media),
             ("implement", page_implement), ("api", page_api), ("history", page_history)]
PAGES = {i18n.tr(f"nav_{key}"): function for key, function in PAGE_KEYS}

language_selector()
st.title(i18n.tr("app_title"))
case_editor()
show_mode()
choice = st.sidebar.radio(i18n.tr("task"), list(PAGES), key="task_nav")
PAGES[choice]()
