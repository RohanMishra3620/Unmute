import json

CATEGORY_TO_KB = {"stress": "stress", "anxiety": "anxiety", "sadness": "low_mood", "low_motivation": "low_mood",
                  "loneliness": "loneliness", "sleep_problem": "sleep_problems", "academic_stress": "academic_stress",
                  "work_stress": "work_stress", "exhaustion": "burnout", "overthinking": "overthinking", "anger": "anger",
                  "social_isolation": "social_isolation", "relationship": "healthy_coping", "hopelessness": "when_to_seek_help",
                  "case_stress": "case_stress", "fear": "fear_safety", "shame_guilt": "shame_guilt", "trauma_memory": "upsetting_memories"}


class KnowledgeAgent:
    """Retrieves coping information from the local knowledge base so the bot never invents mental-health facts."""

    def __init__(self, path):
        with open(path, encoding="utf-8") as f:
            self.entries = json.load(f)

    def retrieve(self, signals, limit=3):
        keys = []
        for s in signals:
            k = CATEGORY_TO_KB.get(s)
            if k and k not in keys:
                keys.append(k)
        if "anxiety" in signals and "breathing_exercises" not in keys:
            keys.append("breathing_exercises")
        if "overthinking" in signals and "grounding_techniques" not in keys:
            keys.append("grounding_techniques")
        return [dict(self.entries[k], key=k) for k in (keys or ["healthy_coping"])[:limit]]

    def get(self, key):
        return dict(self.entries[key], key=key)
