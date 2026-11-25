"""Lab entry point:  python -m src.cli <command>      (python -m src.cli -h for the list)"""
import argparse, importlib.util, sys
from pathlib import Path
from . import axes, context, llm

CASE = context.DEFAULT_CASE.name
ROOT = Path(__file__).resolve().parent.parent


def checks():
    """STEP 0 - return the lab requirement checks as (label, passed, detail) rows."""
    rows = [("Python 3.10+", sys.version_info >= (3, 10), f"  (found {sys.version.split()[0]})")]
    for pkg in ["dotenv", "pandas", "fastapi", "uvicorn", "pydantic", "streamlit"]:
        rows.append((f"package: {pkg}", importlib.util.find_spec(pkg) is not None, ""))
    rows.append(("active provider", llm.current_provider() in llm.PROVIDERS,
                 f"  -> {llm.current_provider()} / {llm.current_model()}"))
    for _, label, ready, key_env, model in llm.provider_status():
        detail = f"  -> model: {model}" if ready else f"  -> optional: set {key_env} in .env"
        rows.append((f"provider: {label} ({key_env})", ready, detail))
    rows.append(("shared case", bool(context.DEFAULT_CASE.name.strip() and context.DEFAULT_CASE.problem.strip()),
                 f"  -> {context.DEFAULT_CASE.name} / {context.DEFAULT_CASE.problem}"))
    rows.append(("sample data", (ROOT / "data/feedback.csv").exists(), ""))
    return rows


def check():
    """Print the requirement checks."""
    ok = lambda b: "OK     " if b else "MISSING"
    for label, passed, detail in checks():
        print(f"{ok(passed)} {label}{detail}")


def main():
    p = argparse.ArgumentParser(description=f"AI Start-up Lab. Running case: {CASE}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="step 0: verify requirements")
    sub.add_parser("case", help="show the shared case brief used by every axis")
    s = sub.add_parser("brainstorm"); s.add_argument("problem", nargs="?", default="students struggle to find internships")
    s = sub.add_parser("extract"); s.add_argument("file", nargs="?", default=str(ROOT / "data/interview.txt"))
    s = sub.add_parser("summarize"); s.add_argument("file", nargs="?", default=str(ROOT / "data/interview.txt"))
    sub.add_parser("compare")
    s = sub.add_parser("analyze"); s.add_argument("file", nargs="?", default=str(ROOT / "data/feedback.csv"))
    sub.add_parser("model")
    sub.add_parser("plan")
    sub.add_parser("media")
    s = sub.add_parser("implement"); s.add_argument("spec", nargs="?", default="a CLI that scores an internship offer from 1-10 using salary, distance and learning value")
    a = p.parse_args()

    if a.cmd == "check":
        check()
    elif a.cmd == "case":
        print(context.get_case().text())
    elif a.cmd == "brainstorm":
        print(axes.brainstorm(a.problem))
    elif a.cmd == "extract":
        print(axes.extract(Path(a.file).read_text(encoding="utf-8")))
    elif a.cmd == "summarize":
        print(axes.summarize(Path(a.file).read_text(encoding="utf-8")))
    elif a.cmd == "compare":
        table, _ = axes.compare(["Mobile app", "WhatsApp bot", "Website"],
                                {"cost": 3, "speed to launch": 2, "reach among students": 3})
        print(table.to_string(index=False) if not table.empty else "No scores (mock mode?). Set an API key.")
    elif a.cmd == "analyze":
        stats, insight = axes.analyze(a.file)
        print(stats, "\n", insight, sep="\n")
    elif a.cmd == "model":
        table, unit = axes.financial_model()
        print(table.to_string(index=False), "\n", unit)
    elif a.cmd == "plan":
        print(axes.plan_to_markdown(axes.plan(CASE)))
    elif a.cmd == "media":
        for k, v in axes.media_prompts("StageFinder", "university students").items():
            print(f"\n## {k}\n{v}")
    elif a.cmd == "implement":
        print("Saved to", axes.implement(a.spec), "- now READ it, then run it.")


if __name__ == "__main__":
    main()
