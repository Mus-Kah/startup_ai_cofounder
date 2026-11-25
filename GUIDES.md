# Tool guides: one tool per axis

Tools change fast. Pick **one tool per axis**, check its current free tier, and keep a prompt library (a simple document). Every coded axis is also available in the browser GUI: run `python app.py`, choose **Workflow** or an individual task from the sidebar, accept the generated preset from the previous axis, edit the inputs, and compare runs in **History & compare**.

## Workflow: make Axis 0..11 a chain
Use **Workflow** for the intended order. Axis 0's prompt output becomes the brainstorm focus; brainstorm becomes research; research becomes extraction text; extraction becomes the summary source; the summary is converted into options and criteria; comparison scores become an analysis table; analysis drives model assumptions; the model drives the roadmap; the roadmap drives the brand brief; the brand brief drives the implementation spec; and the generated code becomes the API handoff. Handoffs are normalized into labeled fields and rows, so a Markdown table from one axis becomes `ITEM 1 / Idea / Target user / Cheapest first test / Main risk` for the next model instead of raw pipe syntax. Open each **View input** expander to inspect the exact handoff, or edit **Edit next input** before running it. Individual task pages now use the same generated preset: Axis 0 starts from the shared case brief, Axis 1..11 start from the previous axis result, and **Reload upstream preset** restores generated values after manual edits. Pressing a run button moves focus to the result area.

## Languages
The sidebar **Language** selector offers English, العربية, and Français. It changes the interface and the output-language instruction sent to every AI prompt. JSON keys, Python code, DataFrame column names, and API fields remain in English so automation still works. Arabic switches the layout to right-to-left. Startup default: `LAB_LANGUAGE=en|ar|fr` in `.env`.

## Shared case brief: keep Axis 0..11 connected
Set the brief once in the sidebar before starting. It contains case name, problem, target user, constraints, and evidence. Every coded AI prompt begins with this brief; every saved result stores the exact brief used; every API response includes it. This is the guard against isolated outputs: if you change the case, run Axis 1..11 again with the same brief. Defaults can be set with `LAB_CASE_NAME`, `LAB_CASE_PROBLEM`, `LAB_CASE_AUDIENCE`, `LAB_CASE_CONSTRAINTS`, and `LAB_CASE_EVIDENCE` in `.env`.

## Code backend: choose an API provider
1. Copy `.env.example` to `.env` and set one provider key, or leave all keys blank for MOCK mode.
2. In the GUI, use the sidebar **LLM API** selector. For the CLI or API service, set `LAB_API_PROVIDER` in `.env`: `auto`, `groq`, `gemini`, `openai`, `qwen`, `openrouter`, `cloudflare`, `nvidia`, `zai`, or `custom`. `auto` chooses the first provider with a key; an explicit provider always wins, even if it has no key and the lab falls back to MOCK mode.
3. Defaults are Groq `openai/gpt-oss-20b` with `GROQ_API_KEY`, Gemini `gemini-3.8-flash` with `GEMINI_API_KEY`, OpenAI `gpt-6.1-terra` with `OPENAI_API_KEY`, and Qwen `qwen-plus` with `DASHSCOPE_API_KEY`.
4. Free no-card choices: OpenRouter `openrouter/free` with `OPENROUTER_API_KEY` (20 requests/minute and 50/day before buying credits), Cloudflare Workers AI `@cf/openai/gpt-oss-20b` with `CLOUDFLARE_API_TOKEN` plus `CLOUDFLARE_ACCOUNT_ID` (10,000 Neurons/day), NVIDIA NIM `meta/llama-3.1-8b-instruct` with `NVIDIA_API_KEY`, and Z.ai `glm-4.7-flash` with `ZAI_API_KEY`. Gemini free tier and Groq free plan are also no-card options, but Gemini unpaid data may be used for product improvement.
5. OpenAI is paid/credit-based; Cerebras requires a payment method for its 30-day trial; Mistral's current API docs require billing. Avoid these if you need a permanently free API.
6. Groq `403` with `error code: 1010` is Cloudflare rejecting Python's default `urllib` user agent. This lab now sends `User-Agent: ai-startup-lab/1.0`; if it still appears, retry on another network or use another free provider.
7. `LAB_API_MODEL` overrides the model for the active provider. `GROQ_BASE_URL`, `OPENAI_BASE_URL`, `QWEN_BASE_URL`, `OPENROUTER_BASE_URL`, `CLOUDFLARE_BASE_URL`, `NVIDIA_BASE_URL`, `ZAI_BASE_URL`, and `CUSTOM_BASE_URL` allow compatible endpoints. Qwen workspace URLs can be pasted into `QWEN_BASE_URL`.
8. For `custom`, set `CUSTOM_API_KEY`, `CUSTOM_BASE_URL`, and `CUSTOM_MODEL` for any OpenAI-compatible chat-completions service.
9. Run `python -m src.cli check` or open the GUI status page to see all providers. A `429` means wait a moment and rerun; the GUI shows the error and elapsed time.

## 0. Prompt engineering (all axes)
**Framework RTCCF:** Role, Task, Context, Constraints, Format.
```
Role: You are a start-up mentor for student founders.
Task: Suggest 5 ways to test demand for an internship-matching app.
Context: Users are university students; budget under $100; 2 weeks.
Constraints: No paid ads, plain language.
Format: Table: test | cost | signal of success.
```
Practices: give examples of the output you want (few-shot), ask the AI to critique its own answer, iterate in short rounds, save prompts that work.

## 1. Brainstorming: Claude / ChatGPT / Gemini
1. Open a chat, paste the RTCCF prompt with your problem. 2. Ask for 20 ideas, then "group them and remove duplicates". 3. Ask for the 3 riskiest assumptions of your favorite.
Practice: diverge (many ideas) then converge (criteria). Never keep the first idea.

## 2. Research: Perplexity, Gemini Deep Research, Elicit
1. Perplexity: ask a precise question ("main internship platforms for students, with links"). 2. Open every cited source. 3. Elicit: find academic papers on your topic. 
Practice: demand sources, cross-check two tools, note the date. An AI without search can invent facts.

## 3. Knowledge extraction: NotebookLM, Claude (file upload), `src/axes.py::extract`
1. NotebookLM: create a notebook, upload interviews, PDFs, articles. 2. Ask: "List the pains mentioned, with the exact quote and the source." 3. In code: `python -m src.cli extract` returns JSON.
Practice: ask for verbatim quotes, use a fixed JSON schema, spot-check 3 items.

## 4. Summarization: NotebookLM, Claude, ChatGPT
Prompt: "Summarize for [audience] in [N] words, then 3 takeaways." Try 3 audiences (investor, user, teammate).
Practice: always state audience and length; compare the summary with the source.

## 5. Comparison: chat AI + Google Sheets
1. Ask for options. 2. **You** fix criteria and weights. 3. Let the AI score 1-5 with reasons. 4. Compute totals in the sheet (or `python -m src.cli compare`).
Practice: define criteria before scoring; do arithmetic in code or Sheets, not in the chat.

## 6. Analysis: Google Sheets + Gemini, Claude/ChatGPT data analysis, pandas
1. Upload `data/feedback.csv`. 2. Ask "average rating by segment, top topics, and a chart". 3. Or run `python -m src.cli analyze`.
Practice: recompute one number by hand; ask what the data cannot tell you.

## 7. Modelling: chat AI + Google Sheets / Excel, `financial_model()`
Ask the AI for a Lean Canvas and a list of assumptions (price, CAC, churn). Put them in cells, then run `python -m src.cli model` to see LTV/CAC and 12 months of cash.
Practice: every assumption has an owner and a source; test a pessimistic and an optimistic case.

## 8. Planning: Notion AI, Trello, chat AI
Prompt: "Plan backwards from launch date, max 3 goals per week, with owner and done-criterion." Export as table with `python -m src.cli plan`.
Practice: weekly review, cut goals instead of extending deadlines.

## 9. Multimedia: Canva, Gamma, Ideogram or Midjourney, ElevenLabs
1. Write a brand brief (name, audience, 3 adjectives, colors). 2. `python -m src.cli media` gives logo/poster prompts and a pitch script. 3. Generate in an image tool, assemble in Canva, build the deck in Gamma.
Practice: check licenses and AI-content rules, keep one consistent palette, never use real people's faces without consent.

## 10. Implementation: Lovable or Bolt (no-code), Cursor or Claude Code, Streamlit
1. Describe the smallest useful slice ("a form that lists internships and filters by field"). 2. Generate, **run**, read the code. 3. `python -m src.cli implement "your spec"` for a Python draft.
Practice: build the smallest slice, test each generated function, commit to Git often, never paste secrets into AI tools.

## 11. Advanced: FastAPI
```bash
pip install -r requirements.txt
uvicorn src.api:app --reload      # open http://127.0.0.1:8000/docs
```
Test `POST /model` with the "Try it out" button. Then call it from any no-code tool (webhook) or a front-end. If the GUI cannot reach this server, it records a `local_fallback` result instead of failing; start uvicorn for a real request.
Practice: validate inputs with Pydantic, keep API keys in `.env` on the server, never in front-end code, add rate limits before going public.

## Troubleshooting
| Problem | Fix |
|---|---|
| Output says MOCK MODE | Set the key for the selected provider in `.env`, or switch the sidebar **LLM API** selector |
| `ModuleNotFoundError` | Activate the venv, rerun `pip install -r requirements.txt` |
| JSON parse error (`raw` key) | Re-run, or lower the task size; the prompt asks for JSON only |
| `uvicorn` not found | `python -m uvicorn src.api:app --reload` |
| `streamlit` not found | Activate the venv, rerun `pip install -r requirements.txt`, then `python app.py` |
| Provider `429` or `403` | Wait and rerun for `429`; for `403` check the selected provider key and update `.env` |
