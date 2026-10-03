"""Thin LLM client supporting Anthropic and OpenAI-compatible endpoints.

Without LLM_API_KEY the client returns a clearly-labelled mock answer, so the
app stays runnable end to end with no credentials.
"""
import requests

from backend import config


class LLMError(Exception):
    pass


def is_configured():
    return bool(config.LLM_API_KEY)


def _mock(user):
    return ("[MOCK MODE - no LLM_API_KEY configured]\n\n"
            "Set LLM_API_KEY and LLM_MODEL in your .env to get real answers.\n\n"
            "Prompt preview:\n" + user[:600])


def _anthropic(system, user, max_tokens, temperature):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": config.LLM_API_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": config.LLM_MODEL, "max_tokens": max_tokens,
              "temperature": temperature, "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=120)
    if r.status_code >= 400:
        raise LLMError("Anthropic API error %s: %s" % (r.status_code, r.text[:300]))
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _openai(system, user, max_tokens, temperature):
    r = requests.post(
        config.LLM_BASE_URL.rstrip("/") + "/chat/completions",
        headers={"Authorization": "Bearer " + config.LLM_API_KEY,
                 "Content-Type": "application/json"},
        json={"model": config.LLM_MODEL, "max_tokens": max_tokens,
              "temperature": temperature,
              "messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}]},
        timeout=120)
    if r.status_code >= 400:
        raise LLMError("LLM API error %s: %s" % (r.status_code, r.text[:300]))
    return r.json()["choices"][0]["message"]["content"]


def complete(system, user, max_tokens=None, temperature=0.2):
    max_tokens = max_tokens or config.LLM_MAX_TOKENS
    if not is_configured():
        return _mock(user)
    try:
        if config.LLM_PROVIDER == "anthropic":
            return _anthropic(system, user, max_tokens, temperature)
        return _openai(system, user, max_tokens, temperature)
    except requests.RequestException as exc:
        raise LLMError("Could not reach the LLM provider: %s" % exc)
