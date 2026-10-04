import re
from collections import Counter

from backend.services.regex_engine import RISK_LEVELS

EMO = {"anxiety": "anxiety", "overthinking": "anxiety", "stress": "stress", "academic_stress": "stress", "work_stress": "stress",
       "sadness": "sadness", "low_motivation": "sadness", "hopelessness": "sadness", "loneliness": "loneliness",
       "social_isolation": "loneliness", "anger": "anger", "exhaustion": "exhaustion", "sleep_problem": "exhaustion",
       "case_stress": "stress", "fear": "anxiety", "trauma_memory": "anxiety", "shame_guilt": "shame"}
INTENS = re.compile(r"\b(very|extremely|so|really|constantly|always|all the time|terrible|awful|unbearable|worst|can'?t (take|handle|cope))\b")


class AnalysisAgent:
    """Turns regex signals (+ optional LLM reading) into structured emotional signals. Never diagnoses."""

    def __init__(self, llm):
        self.llm = llm

    def analyze(self, text, rx, history=(), use_llm=True):
        base = self._heuristic(text, rx)
        if use_llm and self.llm.available:
            base = self._merge(base, self.llm.analyze_message(text, history), rx)
        return base

    def _heuristic(self, text, rx):
        cats = rx["categories"]
        emo_cats = [c for c in cats if c in EMO]
        if not emo_cats:
            res = {"emotion": "neutral", "intensity": 1, "confidence": 0.4, "signals": list(cats), "risk_hint": None}
        else:
            emotion = Counter(EMO[c] for c in emo_cats).most_common(1)[0][0]
            intensity = 3 + len(emo_cats) + (2 if INTENS.search(text.lower()) else 0) + (1 if "hopelessness" in cats else 0)
            res = {"emotion": emotion, "intensity": min(10, intensity), "confidence": round(min(0.9, 0.5 + 0.1 * len(emo_cats)), 2),
                   "signals": list(cats), "risk_hint": None}
        if rx["risk_level"] in ("HIGH_CONCERN", "CRISIS"):
            res["intensity"] = max(res["intensity"], 8)
        res["needs_followup"] = res["emotion"] != "neutral" and res["intensity"] >= 4
        return res

    def _merge(self, base, out, rx):
        if not isinstance(out, dict):
            return base
        try:
            emotion = str(out["emotion"]).lower()[:30]
            intensity = max(1, min(10, int(out["intensity"])))
            conf = max(0.0, min(1.0, float(out["confidence"])))
            extra = [str(s).lower().replace(" ", "_")[:30] for s in (out.get("signals") or [])][:8]
        except (KeyError, TypeError, ValueError):
            return base
        if rx["risk_level"] in ("HIGH_CONCERN", "CRISIS"):
            intensity = max(intensity, 8)
        hint = out.get("risk_level") if out.get("risk_level") in RISK_LEVELS else None
        signals = base["signals"] + [s for s in extra if s not in base["signals"]]
        return {"emotion": emotion, "intensity": intensity, "confidence": round(conf, 2), "signals": signals,
                "needs_followup": emotion != "neutral" and intensity >= 4, "risk_hint": hint}
