from collections import Counter, defaultdict

from backend.services.regex_engine import max_risk, violates_output_policy

TOPICS = {"academic_stress": "academic pressure", "work_stress": "work pressure", "relationship": "relationship difficulties",
          "sleep_problem": "sleep difficulty", "overthinking": "overthinking", "loneliness": "loneliness",
          "social_isolation": "social isolation", "low_motivation": "low motivation", "exhaustion": "emotional exhaustion",
          "anger": "anger or frustration", "hopelessness": "feelings of hopelessness", "stress": "stress",
          "anxiety": "worry", "sadness": "low mood",
          "case_stress": "worry about the case or court process", "fear": "fear and feeling unsafe",
          "shame_guilt": "guilt or shame", "trauma_memory": "upsetting memories"}
GENERIC = {"stress", "anxiety", "sadness"}
CONCERN = ["fear", "trauma_memory", "sleep_problem", "exhaustion", "social_isolation", "loneliness", "low_motivation", "hopelessness"]
POSITIVE = {"positive": "moments of feeling better", "help_seeking": "seeking support", "coping_used": "already using coping strategies"}
DISCLAIMER = "This report is an AI-generated reflection of the conversation, not a medical diagnosis."


def _join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


class ReportAgent:
    def __init__(self, llm, kb, cfg):
        self.llm, self.kb, self.cfg = llm, kb, cfg

    def generate(self, session, messages, analyses):
        users = [m for m in messages if m["role"] == "user"]
        weights, counts, signals = defaultdict(float), Counter(), Counter()
        for a in analyses:
            signals.update(a["signals"])
            if a["emotion"] != "neutral":
                weights[a["emotion"]] += a["intensity"]
                counts[a["emotion"]] += 1
        dominant = sorted(weights, key=lambda e: -weights[e])[:3]
        scores = {e: round(weights[e] / counts[e]) for e in dominant}
        overall = round(sum(scores.values()) / len(scores)) if scores else 0
        risk = max_risk(session["risk_level"], *[a["risk_level"] for a in analyses])
        high = risk in ("HIGH_CONCERN", "CRISIS")

        ordered = [k for k, _ in signals.most_common() if k in TOPICS]
        topics = [TOPICS[k] for k in ([k for k in ordered if k not in GENERIC] or ordered)][:5]
        concerns = [TOPICS[k] for k in CONCERN if k in signals]
        if high:
            concerns.append("statements about personal safety that deserve attention")
        words = sum(len(m["message"].split()) for m in users)
        positives = (["willingness to talk"] if users else []) + (["open communication"] if users and (len(users) >= 3 or words / len(users) >= 8) else [])
        positives += [v for k, v in POSITIVE.items() if k in signals]

        steps = list(self.kb.get("emergency_support")["coping"]) if high else []
        steps += [e["coping"][0] for e in self.kb.retrieve(list(signals))[:3]] if signals else []
        steps.append("Talk with someone you trust about how you have been feeling.")
        steps.append("Please consider speaking with a mental-health professional or crisis service soon." if risk != "SAFE" and (high or risk == "MODERATE_CONCERN")
                     else "Consider professional support if these feelings continue or affect daily life.")
        steps = list(dict.fromkeys(steps))[:6]

        if not dominant:
            state = "No strong emotional signals"
        else:
            state = f"{'Mild' if overall <= 4 else 'Moderate' if overall <= 7 else 'High'} {dominant[0].capitalize()}"
        d = session.get("duration") or 0
        full = self.cfg["SESSION_SECONDS"]
        dur = f"{full // 60} minutes" if d >= full - 2 else f"{d // 60} min {d % 60:02d} s"
        report = {"session_duration": dur, "overall_state": state, "dominant_emotions": dominant, "emotional_intensity": overall,
                  "emotion_scores": scores, "main_topics": topics, "positive_signals": positives, "concerns": concerns,
                  "risk_level": risk, "suggested_next_steps": steps, "disclaimer": DISCLAIMER}
        report["summary"] = self._summary(users, messages, dominant, topics, risk, report)
        return report

    def _summary(self, users, messages, dominant, topics, risk, facts):
        if self.llm.available and users:
            transcript = "\n".join(f"{m['role']}: {m['message']}" for m in messages)
            out = self.llm.generate_report(transcript, {k: facts[k] for k in ("dominant_emotions", "main_topics", "risk_level")})
            s = out.get("summary") if isinstance(out, dict) else None
            if isinstance(s, str) and 0 < len(s) < 700 and not violates_output_policy(s):
                return s.strip()
        if not users:
            return "No messages were shared in this session, so there is not enough to reflect on."
        s = (f"The conversation contained signs of {_join(dominant)}" if dominant else "The conversation did not contain strong emotional signals")
        extra = [t for t in topics if t not in dominant][:3]
        s += f", mainly around {_join(extra)}." if extra and dominant else "."
        s += " You were open about how you were feeling."
        if risk in ("HIGH_CONCERN", "CRISIS"):
            s += " Some statements raised safety concerns, so reaching out to a trusted person or an emergency or crisis service is strongly encouraged."
        return s
