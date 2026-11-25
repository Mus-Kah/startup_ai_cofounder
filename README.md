# AI Start-up Lab: from idea to launch

Hands-on lab for the workshop **"Your AI Co-Founder"** (non-computer-science students).
Running case: **StageFinder**, an app matching students with internships. Replace it with your own idea.

## Step 0: requirements
| Need | Detail |
|---|---|
| Laptop + internet | Any OS, a modern browser |
| Python 3.10+ and VS Code | python.org, code.visualstudio.com; the GUI uses Streamlit |
| Hosted API key (optional) | Groq, Gemini, OpenAI, Qwen, OpenRouter free, Cloudflare Workers AI free, NVIDIA NIM free, Z.ai free, or any OpenAI-compatible endpoint |
| Chat AI account (optional) | Claude, ChatGPT or Gemini for the external-tool comparisons in GUIDES.md |
| API key (optional) | Set one provider key in `.env`; `LAB_API_PROVIDER=auto` picks the first configured provider, or set it to `groq`, `gemini`, `openai`, `qwen`, or `custom`. Defaults: Groq `openai/gpt-oss-20b`, Gemini `gemini-3.8-flash`, OpenAI `gpt-6.1-terra`, Qwen `qwen-plus` |
| Other free accounts | Perplexity, NotebookLM, Canva (see GUIDES.md) |

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then paste one provider key (optional)
python -m src.cli check                              # verifies everything
```

## Browser GUI (recommended)
```bash
python app.py
```
Open the local URL the GUI prints. Extra arguments are passed to the GUI server, for example `python app.py --server.port 8502`. The sidebar has a **Language** selector (English, العربية, Français), an **LLM API** selector for Groq, Google Gemini, OpenAI, Qwen / Model Studio, OpenRouter free, Cloudflare Workers AI free, NVIDIA NIM free, Z.ai free, or a custom OpenAI-compatible endpoint, plus **Workflow** and every individual task: status, prompt lab, brainstorming, research plan, extraction, summarization, comparison, analysis, financial model, planning, media prompts, implementation, API testing, and **History & compare**.

Every task uses the same layout: a left input card with a live preview and a generated preset from the previous axis output, and a right result card with run time, retry, and clear errors. The preset is regenerated when upstream output changes; **Reload upstream preset** restores it after manual edits, and **Custom** lets you keep your own values. Pressing a run button jumps the view to the result card. The status page shows every provider key and the active model. Results from any task are kept for the browser session and can be compared side by side. Uploads, charts, downloads, and explicit code saving are available; the CLI commands below still work. `app.py` is the stable entry point, so the command stays the same if the GUI library changes.

## Shared case brief (keeps the 12 axes connected)
The sidebar **Shared case brief** is the single source of truth for case name, problem, target user, constraints, and evidence. It is prepended to every AI prompt, attached to every saved result, and returned by the API endpoints, so Axis 1..11 cannot silently drift away from Axis 0. Use **Apply to task fields** to copy the brief into task inputs, or **Reset case** to restore the default. CLI/API defaults come from `LAB_CASE_*` in `.env`; run `python -m src.cli case` to print the active brief.

## Workflow (output -> next input)
**Workflow** is the default page. It runs Axis 0 to 11 in order and adapts each output into the next axis input: prompt -> brainstorm -> research plan -> extracted insights -> summary -> options and criteria -> comparison table -> analysis frame -> model assumptions -> roadmap -> brand brief -> implementation spec -> API request. Each handoff is normalized into labeled text or rows, never copied as a raw Markdown table, so the next model receives clear field names and source notes. Each handoff is shown and editable before it runs, so you can inspect the chain instead of trusting it blindly. Individual task pages receive the same generated preset; Axis 0 starts from the shared case brief, and Axis 1..11 start from the latest output of the previous axis. Manual results and workflow results both feed these presets.

## Languages
Choose **English**, **العربية**, or **Français** in the sidebar. The interface, page names, generated preset labels, status messages, and shared case labels switch immediately. Arabic uses right-to-left layout. AI prompts also receive an output-language instruction, while JSON keys, code, and column names stay stable so the chain keeps working. Set the startup language with `LAB_LANGUAGE=en|ar|fr` in `.env`.

## Step 1..5: problem -> axis -> command
| Start-up problem | Axis | Command |
|---|---|---|
| What should we build? | 1 Brainstorming | `python -m src.cli brainstorm "your problem"` |
| What do users really say? | 3 Extraction, 4 Summarization | `python -m src.cli extract` / `summarize` |
| Which option wins? | 5 Comparison | `python -m src.cli compare` |
| What does the feedback tell us? | 6 Analysis | `python -m src.cli analyze` |
| Will the numbers work? | 7 Modelling | `python -m src.cli model` |
| What is our 8-week plan? | 8 Planning | `python -m src.cli plan` |
| Brand + pitch? | 9 Multimedia | `python -m src.cli media` |
| First prototype? | 10 Implementation | `python -m src.cli implement` |
| Serve it to any app | 11 FastAPI | `uvicorn src.api:app --reload` then open `/docs` |

If uvicorn is not running, Axis 11 no longer fails: the GUI marks the result `local_fallback`, echoes the handoff and shared case locally, and keeps the chain complete. Start the service when you want a real HTTP call.

Axes 0 (prompting) is in `src/prompts.py`;
 axis 2 (research) uses live tools, see GUIDES.md. `WORKSHOP_SCENARIO.tex` is a short LaTeX walkthrough from Axis 0 to Axis 11 ending in a concrete launch pack.

## Project map
- `src/prompts.py`: RTCCF prompt builder (Role, Task, Context, Constraints, Format)
- `src/context.py`: shared case brief used by every axis
- `src/i18n.py`: English, Arabic, and French interface strings
- `src/pipeline.py`: output-to-input adapters for the 12-axis workflow
- `src/axes.py`: one function per axis
- `src/llm.py`: multi-provider LLM wrapper with mock fallback
- `app.py`: browser GUI entry point for every task (`python app.py`)
- `src/cli.py`: lab commands, `src/api.py`: FastAPI service
- `data/`: sample interview and feedback survey, `outputs/`: generated files

## Rules of the lab
1. AI drafts, **you verify**: check every number, quote and line of code.
2. No personal or confidential data in prompts.
3. Change one thing at a time: edit the prompt in `axes.py`, rerun, compare.
4. In the GUI, generated code is only written to `outputs/` when you press **Save draft**.
