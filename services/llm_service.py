"""Provider-agnostic LLM wrapper. Every method returns None on any failure so callers use their rule-based fallback."""
import json
import logging

import requests

log = logging.getLogger(__name__)

ANALYZE_SYSTEM = ("You analyse one message from an emotional-support chat. Reply with ONLY a JSON object: "
                  '{"emotion": one of anxiety|stress|sadness|loneliness|anger|exhaustion|neutral, "intensity": 1-10, '
                  '"confidence": 0-1, "signals": [short snake_case strings], '
                  '"risk_level": one of SAFE|LOW_CONCERN|MODERATE_CONCERN|HIGH_CONCERN|CRISIS}. '
                  "Be conservative about safety: escalate if the user hints at self-harm, suicide or harming others. Do not diagnose.")
REPORT_SYSTEM = ("You write a short, kind, non-clinical reflection (max 3 sentences) of a support conversation. "
                 "Use phrases like 'the conversation contained signs of...'. Never diagnose, never name disorders, never mention medication. "
                 'Reply with ONLY JSON: {"summary": "..."}')


def _merge_roles(messages):
    out = []
    for m in messages:
        if out and out[-1]["role"] == m["role"]:
            out[-1]["content"] += "\n" + m["content"]
        else:
            out.append(dict(m))
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _json(text):
    try:
        return json.loads(text[text.index("{"): text.rindex("}") + 1])
    except Exception:
        return None


class LLMService:
    def __init__(self, cfg):
        self.provider = cfg.get("LLM_PROVIDER", "openai")
        self.key, self.model = cfg.get("LLM_API_KEY", ""), cfg.get("LLM_MODEL", "")
        self.base = (cfg.get("LLM_BASE_URL") or "").rstrip("/")
        self.timeout = cfg.get("LLM_TIMEOUT", 12)
        if self.provider == "anthropic" and "openai.com" in self.base:
            self.base = "https://api.anthropic.com/v1"

    @property
    def available(self):
        return bool(self.key and self.model)

    def _complete(self, system, messages, max_tokens=200, temperature=0.5):
        if not self.available:
            return None
        messages = _merge_roles(messages)
        try:
            if self.provider == "anthropic":
                r = requests.post(f"{self.base}/messages", timeout=self.timeout,
                                  headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                                  json={"model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                                        "system": system, "messages": messages})
                r.raise_for_status()
                return "".join(b.get("text", "") for b in r.json().get("content", []))
            r = requests.post(f"{self.base}/chat/completions", timeout=self.timeout,
                              headers={"Authorization": f"Bearer {self.key}"},
                              json={"model": self.model, "max_tokens": max_tokens, "temperature": temperature,
                                    "messages": [{"role": "system", "content": system}] + messages})
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("LLM call failed, using fallback: %s", e)
            return None

    @staticmethod
    def _hist(history, limit=14):
        return [{"role": m["role"], "content": m["message"]} for m in history[-limit:]]

    def generate_response(self, system, history, user_message):
        # higher temperature = replies that feel human and differ every time
        return self._complete(system, self._hist(history) + [{"role": "user", "content": user_message}], 220, 0.85)

    def analyze_message(self, text, history=()):
        out = self._complete(ANALYZE_SYSTEM, [{"role": "user", "content": text}], 150, 0)
        return _json(out) if out else None

    def generate_report(self, transcript, facts):
        out = self._complete(REPORT_SYSTEM, [{"role": "user", "content": f"Facts: {json.dumps(facts)}\n\nTranscript:\n{transcript[-4000:]}"}], 250, 0.3)
        return _json(out) if out else None
