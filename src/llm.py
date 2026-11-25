"""One tiny wrapper around several hosted LLMs. Every lab function goes through ask() / ask_json()."""
import json, os, re, urllib.error, urllib.parse, urllib.request
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "groq": {"label": "Groq", "key_env": "GROQ_API_KEY", "model_env": "GROQ_MODEL",
             "default_model": "openai/gpt-oss-20b", "base_env": "GROQ_BASE_URL",
             "default_base": "https://api.groq.com/openai/v1", "style": "openai"},
    "gemini": {"label": "Google Gemini", "key_env": "GEMINI_API_KEY", "model_env": "GEMINI_MODEL",
               "default_model": "gemini-3.8-flash", "style": "gemini"},
    "openai": {"label": "OpenAI", "key_env": "OPENAI_API_KEY", "model_env": "OPENAI_MODEL",
               "default_model": "gpt-6.1-terra", "base_env": "OPENAI_BASE_URL",
               "default_base": "https://api.openai.com/v1", "style": "openai"},
    "qwen": {"label": "Qwen / Model Studio", "key_env": "DASHSCOPE_API_KEY", "model_env": "QWEN_MODEL",
             "default_model": "qwen-plus", "base_env": "QWEN_BASE_URL",
             "default_base": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "style": "openai"},
    "openrouter": {"label": "OpenRouter free", "key_env": "OPENROUTER_API_KEY", "model_env": "OPENROUTER_MODEL",
                   "default_model": "openrouter/free", "base_env": "OPENROUTER_BASE_URL",
                   "default_base": "https://openrouter.ai/api/v1", "style": "openai"},
    "cloudflare": {"label": "Cloudflare Workers AI free", "key_env": "CLOUDFLARE_API_TOKEN",
                   "model_env": "CLOUDFLARE_MODEL", "default_model": "@cf/openai/gpt-oss-20b",
                   "base_env": "CLOUDFLARE_BASE_URL", "account_env": "CLOUDFLARE_ACCOUNT_ID",
                   "default_base": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
                   "style": "openai"},
    "nvidia": {"label": "NVIDIA NIM free", "key_env": "NVIDIA_API_KEY", "model_env": "NVIDIA_MODEL",
               "default_model": "meta/llama-3.1-8b-instruct", "base_env": "NVIDIA_BASE_URL",
               "default_base": "https://integrate.api.nvidia.com/v1", "style": "openai"},
    "zai": {"label": "Z.ai free", "key_env": "ZAI_API_KEY", "model_env": "ZAI_MODEL",
            "default_model": "glm-4.7-flash", "base_env": "ZAI_BASE_URL",
            "default_base": "https://api.z.ai/api/paas/v4", "style": "openai"},
    "custom": {"label": "Custom OpenAI-compatible", "key_env": "CUSTOM_API_KEY", "model_env": "CUSTOM_MODEL",
               "default_model": "", "base_env": "CUSTOM_BASE_URL", "default_base": "", "style": "openai"},
}


AUTO_PROVIDER = "auto"
USER_AGENT = "ai-startup-lab/1.0"


def current_provider():
    name = os.getenv("LAB_API_PROVIDER", AUTO_PROVIDER).strip().lower() or AUTO_PROVIDER
    if name == AUTO_PROVIDER:
        for candidate, spec in PROVIDERS.items():
            if os.getenv(spec["key_env"]):
                return candidate
        return "groq"
    return name if name in PROVIDERS else "groq"


def set_provider(name, model=None):
    if name != AUTO_PROVIDER and name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}")
    os.environ["LAB_API_PROVIDER"] = name
    if model is None:
        os.environ.pop("LAB_API_MODEL", None)
    else:
        os.environ["LAB_API_MODEL"] = model
    return name


def current_model():
    name = current_provider()
    spec = PROVIDERS[name]
    return os.getenv("LAB_API_MODEL") or os.getenv(spec["model_env"], spec["default_model"])


def provider_status():
    return [(name, spec["label"], bool(os.getenv(spec["key_env"])), spec["key_env"],
             os.getenv("LAB_API_MODEL") or os.getenv(spec["model_env"], spec["default_model"]))
            for name, spec in PROVIDERS.items()]


def configured(name=None):
    spec = PROVIDERS[name or current_provider()]
    return bool(os.getenv(spec["key_env"]))


def post_json(url, headers, payload):
    headers = {"User-Agent": USER_AGENT, **headers}
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403 and "1010" in detail:
            detail += " (Cloudflare blocked the client fingerprint; this app sends a descriptive User-Agent, so retry or try another network/provider.)"
        raise RuntimeError(f"API error {exc.code}: {detail[:500]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Connection error: {exc.reason}") from exc


def base_for(spec):
    base = os.getenv(spec.get("base_env", ""), spec.get("default_base", "")).rstrip("/")
    if "{account_id}" in base:
        account = os.getenv(spec.get("account_env", ""), "")
        if not account:
            raise RuntimeError(f"Set {spec['account_env']} for {spec['label']}.")
        base = base.format(account_id=account)
    return base


def ask_openai_compatible(prompt, system, max_tokens, spec, name, key, model):
    base = base_for(spec)
    if not base or not model:
        raise RuntimeError(f"Set {spec.get('base_env', 'API_BASE_URL')} and {spec['model_env']} for {spec['label']}.")
    payload = {"model": model,
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
               "temperature": 0.4}
    payload["max_completion_tokens" if name in ("groq", "openai") else "max_tokens"] = max_tokens
    if name == "groq" and model.startswith("openai/gpt-oss"):
        payload["reasoning_effort"] = "low"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if name == "openrouter":
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
        headers["X-OpenRouter-Title"] = os.getenv("OPENROUTER_APP_TITLE", "AI Start-up Lab")
    data = post_json(base + "/chat/completions", headers, payload)
    return data["choices"][0]["message"].get("content") or ""


def ask_gemini(prompt, system, max_tokens, key, model):
    if not model:
        raise RuntimeError("Set GEMINI_MODEL for Google Gemini.")
    query = urllib.parse.urlencode({"key": key})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model, safe='')}:generateContent?{query}"
    payload = {"systemInstruction": {"parts": [{"text": system}]},
               "contents": [{"role": "user", "parts": [{"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4}}
    data = post_json(url, {"Content-Type": "application/json"}, payload)
    return data["candidates"][0]["content"]["parts"][0].get("text", "")


def ask(prompt: str, system: str = "You are a helpful, honest start-up mentor.", max_tokens: int = 1200) -> str:
    name = current_provider()
    spec = PROVIDERS[name]
    key = os.getenv(spec["key_env"])
    model = current_model()
    if not key:
        return (f"[MOCK MODE - active provider is {spec['label']}; set {spec['key_env']} in .env "
                f"or choose another API in the GUI]\n\nPrompt sent:\n{prompt[:400]}")
    if spec["style"] == "gemini":
        return ask_gemini(prompt, system, max_tokens, key, model)
    return ask_openai_compatible(prompt, system, max_tokens, spec, name, key, model)


def ask_json(prompt: str, **kw):
    """Ask for JSON and parse it safely (structured output = the bridge to code)."""
    text = ask(prompt + "\n\nReturn ONLY valid JSON. No markdown fences, no commentary.", **kw)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
