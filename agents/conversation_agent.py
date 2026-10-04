"""Conversation agent: the 'therapist-style' voice of Unmute.

Two paths, same rules:
  1. LLM path (if LLM_API_KEY + LLM_MODEL are set): a fresh reply is written for every message, guided by the
     session stage, the detected emotion and the replies already given (so it does not repeat itself).
  2. Offline path: replies are composed from many small parts (acknowledgement + the person's own words +
     one easy question or one coping step) and never reuse a sentence already said in this session.
Language is kept simple, warm Indian English. The agent never diagnoses and never claims to be a human or therapist.
"""
import random
import re

from services.regex_engine import violates_output_policy

SYSTEM = (
    "You are Unmute, a gentle support companion in a short 5-minute check-in. You are an AI, not a doctor, therapist or "
    "counsellor, and you never say otherwise. The person may be going through a very hard time (for example fear, a police or "
    "court case, family pressure, or past trauma).\n"
    "VOICE: simple, warm Indian English, like a kind elder sibling. Short everyday words. No jargon, no American slang, no emojis, "
    "no lists. Phrases such as 'I understand', 'that must be very tiring', 'take your time' are welcome.\n"
    "EACH REPLY: 2 or 3 short sentences. First, reflect something specific the person just said, using their own words. Then ask "
    "exactly ONE easy, open question, or offer ONE small coping step taken from the notes and ask if it feels possible. "
    "If they give very short answers, offer two easy choices to pick from.\n"
    "NEVER repeat a sentence, question or opening you already used in this chat; move forward each turn "
    "(what happened -> how it feels -> what helps -> one small next step).\n"
    "NEVER diagnose, never mention medicines, never give legal advice or promise how a case will end, never give self-harm "
    "information, never claim to be human.\n"
)
STAGE_NOTE = {
    "open": "This is the start. Welcome them gently and let them share at their own pace.",
    "explore": "Understand what is happening: the situation, since when, who is involved.",
    "feel": "Go a little deeper into feelings and body sensations. Do not rush to solutions.",
    "help": "Gently move to one small practical step from the notes, and check if it feels possible.",
    "close": "Time is nearly over. Kindly sum up in one line, share one small tip, and thank them.",
}
CHIPS = {
    "open": ["I am feeling stressed", "I am worried about my case", "I cannot sleep properly", "I feel scared or alone", "I am doing okay today"],
    "explore": ["Let me explain", "I don't know where to start", "Something happened today"],
    "feel": ["I feel it in my body", "My thoughts don't stop", "I feel numb"],
    "help": ["Yes, let us try", "Please give me a simple tip", "I need to think"],
    "close": ["Thank you"],
}

# ---------------------------------------------------------------- acknowledgements (one sentence each)
ACK = {
    "anxiety": ["That sounds really worrying, and it is natural for the mind to feel restless like this.",
                "Feeling this much tension is very tiring, and it does not mean you are weak.",
                "I understand, when worry keeps running in the mind it is hard to relax.",
                "Thank you for telling me, anyone would feel uneasy in such a situation.",
                "That must be uncomfortable for you, both in the mind and in the body."],
    "stress": ["That sounds like a lot to carry on your shoulders.",
               "I can understand why you are feeling so much pressure.",
               "It makes sense that you feel stretched when so much is happening together.",
               "Thank you for sharing this, it is not easy to manage so many things at once.",
               "That must be exhausting, and you are doing your best in a difficult time."],
    "sadness": ["I am sorry you are feeling this low, that sounds really heavy.",
                "It is okay to feel sad, and you do not have to hide it here.",
                "That sounds painful, and I am glad you are talking about it.",
                "Thank you for trusting me with this, it takes courage to say it.",
                "I can hear how much this is hurting you."],
    "loneliness": ["Feeling alone can hurt a lot, and I am glad you told me.",
                   "That sounds very lonely, and you do not have to go through it by yourself right now.",
                   "I hear you, it is hard when nobody seems to understand.",
                   "Thank you for opening up, I am here and I am listening."],
    "anger": ["I can hear how frustrated you are, and your feelings are valid.",
              "That sounds really upsetting, anyone would feel angry in such a situation.",
              "It is okay to feel angry, it often shows that something important to you was hurt.",
              "Thank you for saying it openly, that anger has a reason behind it."],
    "exhaustion": ["That sounds very draining, as if you have been running on empty for a long time.",
                   "You must be so tired, in the body as well as in the mind.",
                   "It is understandable to feel worn out after carrying so much.",
                   "Thank you for telling me, your tiredness is real and it matters."],
    "shame": ["Thank you for sharing something so personal, I know it is not easy to say.",
              "What you feel is heavy, and many people carry such feelings in silence.",
              "I hear you, and I want you to know that you are not being judged here."],
}
TOPIC_ACK = {
    "case_stress": ["Waiting for the case and the legal process can be very tiring and frightening.",
                    "Going through hearings and repeating your story again and again is not easy at all.",
                    "It is natural to feel nervous about the case, it is a big thing in anyone's life."],
    "fear": ["Feeling afraid like this is very hard, and your fear is taken seriously here.",
             "It sounds like your mind and body are on alert, which is very tiring.",
             "Thank you for telling me about this fear, it takes strength to say it."],
    "trauma_memory": ["Memories that keep coming back can be very disturbing, and I am sorry you are facing this.",
                      "That sounds really painful, as if the past does not let you rest.",
                      "Thank you for sharing this, such memories are very heavy to carry."],
    "sleep_problem": ["Not sleeping well makes everything else feel heavier.",
                      "Sleepless nights are really draining, I understand.",
                      "When sleep does not come, the mind gets tired and worried together."],
    "academic_stress": ["Exam and study pressure can feel very heavy, especially with everyone's expectations.",
                        "That sounds like a lot of pressure from studies."],
    "work_stress": ["Work pressure can follow us even after we reach home, I understand.",
                    "That sounds like a stressful time at work."],
    "relationship": ["Problems with people close to us hurt the most.",
                     "It is painful when family or close people do not understand us."],
}
HIGH_ACK = ["That sounds very heavy, and I am glad you are sharing it with me.",
            "I can feel how much pain is in your words, and I am here with you.",
            "This is a lot to carry alone, so thank you for trusting me with it."]
ACK_ANY = ["Thank you for telling me this, I am listening.", "I can see this matters a lot to you.",
           "That is not easy to talk about, and I am glad you did.", "I am here with you, so please take your time.",
           "What you are going through is real, and it deserves care.", "You are doing well by putting this into words.",
           "I understand, and I do not think any less of you for it.", "It takes courage to say this out loud."]
NORMALISE = ["Many people feel like this in such times, so you are not alone in it.",
             "What you are feeling is a natural reaction to a very difficult situation.",
             "There is nothing wrong with you for feeling this way."]

# ---------------------------------------------------------------- questions (one easy question each)
Q_TOPIC = {
    "case_stress": {"explore": ["Which part of the case is worrying you the most right now?",
                                "Is it the waiting, the hearing, or facing certain people that feels most difficult?"],
                    "feel": ["When you think about the next hearing, what do you feel in your body?",
                             "What is the thought that comes again and again about the case?"],
                    "help": ["Is there someone who can sit with you on the day of the hearing?",
                             "What would make the hearing day a little easier for you?"]},
    "fear": {"explore": ["Do you feel safe where you are right now?",
                         "When does the fear come the most, day time or night time?"],
             "feel": ["What does the fear make you want to do, run away, hide or stay alert?",
                      "Is there any place or person that makes the fear a little less?"],
             "help": ["Who is the one person you can call if you feel afraid?",
                      "Which place feels the safest for you?"]},
    "trauma_memory": {"explore": ["Do these memories come mostly at night or also during the day?",
                                  "You do not have to tell me the details. How often do they come now?"],
                      "feel": ["When a memory comes, what happens in your body?",
                               "What helps you come back to the present, even a little?"],
                      "help": ["Would you like to try a small grounding step now?"]},
    "sleep_problem": {"explore": ["How many hours are you getting at night these days?",
                                  "Is it difficult to fall asleep, or do you wake up in between?"],
                      "feel": ["What goes on in your mind when you lie down at night?",
                               "Do you feel more tired or more worried in the daytime?"],
                      "help": ["What is your routine in the last hour before sleep?"]},
    "academic_stress": {"explore": ["Which subject or exam is troubling you the most?",
                                    "Is the pressure coming from yourself or from others?"],
                        "feel": ["What do you fear will happen if the result is not good?"],
                        "help": ["What is one small topic you can finish today?"]},
    "work_stress": {"explore": ["What is the hardest part of your work these days?",
                                "Do you get any time to rest after work?"],
                    "feel": ["What do you feel when you think of tomorrow's work?"],
                    "help": ["What is one thing you can leave for tomorrow?"]},
    "relationship": {"explore": ["Who is this about, someone at home or a friend?",
                                 "What happened that hurt you the most?"],
                     "feel": ["How do you feel when you are around this person?"],
                     "help": ["Is there someone else who understands you better?"]},
    "shame_guilt": {"explore": ["What is the thought that makes you feel this way?"],
                    "feel": ["If your close friend felt the same, what would you tell them?"],
                    "help": ["Is there one person who will listen without judging you?"]},
}
Q_EMO = {
    "anxiety": {"explore": ["What is the worry that comes first in your mind?", "When did this worry start feeling stronger?"],
                "feel": ["Where do you feel the worry in your body, chest, stomach or head?",
                         "What is the worst thing your mind keeps telling you?"],
                "help": ["Shall we try one slow breath together right now?"]},
    "stress": {"explore": ["What is weighing on you the most these days?", "How long have you been feeling this pressure?"],
               "feel": ["How is this stress showing up, in your sleep, food or mood?",
                        "What do you do when it becomes too much?"],
               "help": ["What is one thing that can be made lighter this week?"]},
    "sadness": {"explore": ["Since when have you been feeling like this?", "Was there any event that started this feeling?"],
                "feel": ["What part of the day feels the heaviest?", "What do you miss the most these days?"],
                "help": ["What is one small thing that gave you a little comfort earlier?"]},
    "loneliness": {"explore": ["When do you feel the most alone?", "Is there anyone you wish to talk to but are not able to?"],
                   "feel": ["What would it feel like to have someone beside you right now?"],
                   "help": ["Who is one person you could send a short message to today?"]},
    "anger": {"explore": ["What happened just before you started feeling this angry?", "Who or what is this anger about?"],
              "feel": ["What does the anger want to say, if it could speak?"],
              "help": ["What helps you cool down, a walk, water, or some music?"]},
    "exhaustion": {"explore": ["What has been taking most of your energy?", "How have your sleep and meals been?"],
                   "feel": ["When did you last get some proper rest?"],
                   "help": ["What is one thing you can say no to this week?"]},
    "shame": {"explore": ["Would you like to tell me a little more, only if you feel comfortable?"],
              "feel": ["What does this feeling say about you, in your own mind?"],
              "help": ["Who is one person you feel safe with?"]},
}
Q_GENERIC = {
    "open": ["What would you like to talk about today?", "What has been on your mind the most these days?"],
    "explore": ["Can you tell me a little more about what has been happening?",
                "Is it something at home, at work or college, or something else?",
                "Since when have you been feeling this way?",
                "What part of this is on your mind the most?"],
    "feel": ["How are you feeling inside as we talk about this?",
             "What is the hardest part for you, at this moment?",
             "How much is this affecting your daily routine?",
             "What do you need the most right now, rest, support or just someone to listen?"],
    "help": ["What has helped you even a little in the past, when you felt like this?",
             "What is one small thing you can do today just for yourself?",
             "Who is the one person you feel a little safe with?"],
}
ADV_LEADS = ["Thank you for asking, I am happy to share something simple.", "Of course, let us find something small and doable.",
             "I am glad you asked, a small step can help.", "Sure, here is something gentle you can try."]
TIP_LEADS = ["One small thing that may help: {t}", "If you feel like it, you could try this: {t}",
             "Some people find this useful: {t}", "A gentle idea for you: {t}"]
TIP_CHECKS = ["Does that feel possible for you?", "How does that sound to you?", "Would you like to try it today?",
              "Do you think you can try this once?", "Is this something you can do, even for two minutes?"]

# ---------------------------------------------------------------- special situations
GREET = re.compile(r"^(hi+|hello+|hey+|hii+|namaste|namaskar|good (morning|afternoon|evening))\b")
THANKS = re.compile(r"\b(thanks|thank you|thankyou|shukriya|dhanyavad)\b")
WHO = re.compile(r"\b(are you (a )?(real|human|bot|robot|ai|person)|who are you|is this a (bot|human|person))\b")
ADVICE = re.compile(r"\b(what (should|can|do) i do|any (tip|tips|advice|suggestion)|give me (a )?(tip|advice)|how (do|can) i (cope|feel better|handle|deal)|help me|simple tip)\b")
SHORT = {"ok", "okay", "yes", "no", "hmm", "hm", "idk", "fine", "nothing", "maybe", "yeah", "yep", "nope", "k", "not sure"}
POS = {
    "ack": ["I am really glad to hear that.", "That is lovely to hear.", "It is nice that you are feeling a little better."],
    "q": ["What has been helping you feel this way?", "What made today a little easier for you?",
          "What is one thing you want to keep doing, so this feeling stays?"],
}
GREET_R = ["Namaste, I am glad you are here. There is no hurry, so take your time. What would you like to talk about today?",
           "Hello, it is good to have you here. You can share anything at your own pace. How has your day been so far?"]
THANKS_R = ["You are most welcome. I am here as long as we have time, so what else is on your mind?",
            "I am glad it helped even a little. Is there anything else you would like to share?"]
WHO_R = ["I am an AI support tool, not a human or a doctor, but I am listening carefully to every word you say. What would you like to share?",
         "You are talking to an AI, not a person. Even then, your feelings matter here. What is on your mind?"]
SHORT_R = ["That is okay, you do not have to say much. Would it be easier to tell me if it is more about your mind, your body, or your situation?",
           "No problem, take your time. We can go slowly, so tell me, is today a heavy day or a light day?",
           "It is alright if words are hard to find. Shall I ask a simple question, like what was the hardest moment of today?",
           "Short answers are fine, I am not in a hurry. Is there one word that describes how today has been?",
           "Thank you for being here, even when it is hard to talk. Would you like to tell me about the last time you felt a little peaceful?",
           "We can keep it very simple. Is something worrying you, hurting you, or just tiring you?",
           "It is okay to be quiet for a moment. When you are ready, tell me who or what is on your mind right now.",
           "You are doing fine, there is no right answer. Should we talk about your day, your night, or your thoughts?"]
CLOSE_1 = ["We are almost at the end of our time.", "Our time is nearly over for today.", "We have only a little time left."]
CLOSE_3 = ["Thank you for sharing with me today, please take care of yourself.",
           "Thank you for trusting me today, and please be kind to yourself.",
           "I am glad you talked today, and please reach out to someone you trust."]


def _lower(s):
    return s[0].lower() + s[1:] if s else s


def _sents(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]


_P = [(r"\bi am\b", "you are"), (r"\bi'm\b", "you are"), (r"\bi was\b", "you were"), (r"\bi've\b", "you have"),
      (r"\bi'll\b", "you will"), (r"\bi'd\b", "you would"), (r"\bmyself\b", "yourself"), (r"\bmy\b", "your"),
      (r"\bmine\b", "yours"), (r"\bme\b", "you"), (r"\bi\b", "you")]


def _echo(text):
    """Return a short clause in the person's own words, turned from 'I' to 'you', or None."""
    t = text.replace("\u2019", "'").strip()
    for clause in re.split(r"[.!?;,\n]| but | because | and then | so ", t, flags=re.I):
        c = clause.strip()
        if not (3 <= len(c.split()) <= 11) or not re.match(r"(?i)(i\b|i'|my\b)", c) or re.search(r"[\d@/]", c):
            continue
        for pat, rep in _P:
            c = re.sub(pat, rep, c, flags=re.I)
        return _lower(c)
    return None


def _stage(turn, remaining):
    if remaining <= 45:
        return "close"
    if turn == 0:
        return "open"
    if turn <= 2:
        return "explore"
    if turn <= 4 and remaining > 100:
        return "feel"
    return "help"


class ConversationAgent:
    def __init__(self, llm):
        self.llm = llm

    # public API ---------------------------------------------------------------------------------------------
    def respond(self, *a, **kw):
        return self.respond_full(*a, **kw)["reply"]

    def respond_full(self, text, history, analysis, entries, turn, remaining, session_risk="SAFE"):
        stage = _stage(turn, remaining)
        reply = None
        if self.llm.available:
            reply = self._llm_reply(text, history, analysis, entries, stage, remaining)
        chips = CHIPS[stage]
        if not reply:
            reply, override = self._fallback(text, history, analysis, entries, turn, stage)
            chips = override or chips
        return {"reply": reply, "suggestions": chips, "stage": stage}

    # LLM path -----------------------------------------------------------------------------------------------
    def _llm_reply(self, text, history, analysis, entries, stage, remaining):
        notes = "\n".join(f"- {e['title']}: {'; '.join(e['coping'])}" for e in entries)
        said = [m["message"] for m in history if m["role"] == "assistant"][-4:]
        system = (SYSTEM + f"\nSTAGE: {STAGE_NOTE[stage]}\nDetected emotion: {analysis['emotion']} (intensity {analysis['intensity']}/10); "
                  f"signals: {', '.join(analysis['signals']) or 'none'}.\nSeconds left: {remaining}.\nCoping notes (use only these ideas):\n{notes}\n"
                  + ("Things you already said (do not repeat them):\n" + "\n".join(f"- {s}" for s in said) if said else ""))
        out = self._clean(self.llm.generate_response(system, history, text))
        if out and not violates_output_policy(out) and not self._repeats(out, said):
            return out
        return None

    @staticmethod
    def _clean(out):
        if not out:
            return None
        parts = _sents(" ".join(out.split()))[:3]
        kept = ""
        for p in parts:
            if len(kept) + len(p) > 420 and kept:
                break
            kept = f"{kept} {p}".strip()
        return kept or None

    @staticmethod
    def _repeats(out, said):
        a = set(re.findall(r"[a-z']+", out.lower()))
        for s in said:
            b = set(re.findall(r"[a-z']+", s.lower()))
            if a and b and len(a & b) / len(a | b) > 0.6:
                return True
        return False

    # offline path -------------------------------------------------------------------------------------------
    def _fallback(self, text, history, analysis, entries, turn, stage):
        rng = random.Random(f"{turn}|{text}")
        used = {s.lower() for m in history if m["role"] == "assistant" for s in _sents(m["message"])}

        prior = " ".join(m["message"] for m in history if m["role"] == "assistant").lower()

        def fresh_tips(entries):
            pool = [t for e in entries for t in e["coping"]] or ["Take a few slow breaths and relax your shoulders."]
            return [t for t in pool if t.lower().rstrip(".") not in prior] or pool

        def pick(options, strict=False):
            fresh = [o for o in options if not any(x.lower() in used for x in _sents(o))]   # sentence-level, so no part repeats
            if strict and not fresh:
                return None
            choice = rng.choice(fresh or options)
            used.update(x.lower() for x in _sents(choice))
            return choice

        emo, sig, inten = analysis["emotion"], analysis["signals"], analysis["intensity"]
        t = text.lower().strip().replace("\u2019", "'")
        words = t.split()

        if stage == "close":
            return self._close(pick, fresh_tips(entries)), CHIPS["close"]
        if emo == "neutral":
            talk = CHIPS["open"] if turn <= 1 else CHIPS["explore"]
            if GREET.match(t) and len(words) <= 4:
                return pick(GREET_R), CHIPS["open"]
            if WHO.search(t):
                return pick(WHO_R), talk
            if THANKS.search(t):
                return pick(THANKS_R), talk
            if len(words) <= 2 or t.strip(" .!") in SHORT:
                short = pick(SHORT_R, True) or f"{pick(ACK_ANY, True) or 'I am listening.'} {self._question(pick, 'neutral', [], 'feel')}"
                return short, ["My mind", "My body", "My situation", "Today was heavy"]
            if "positive" in sig:
                return f"{pick(POS['ack'])} {pick(POS['q'])}", None
            if ADVICE.search(t):
                return self._tip_reply(pick, fresh_tips(entries), pick(ADV_LEADS, True) or pick(ACK_ANY)), CHIPS["help"]
            ech = _echo(text)
            lead = f"I hear you, so {ech}." if ech else "Thank you for sharing that with me."
            return f"{lead} {pick(Q_GENERIC['explore' if stage == 'open' else stage])}", None
        if ADVICE.search(t) or stage == "help":
            ack = pick(self._acks(emo, sig, inten, rng), True) or pick(ACK_ANY)
            return self._tip_reply(pick, fresh_tips(entries), ack), CHIPS["help"]

        parts = [pick(self._acks(emo, sig, inten, rng), True) or pick(ACK_ANY, True)]
        parts = [p for p in parts if p]
        ech = _echo(text)
        echo_line = rng.choice(["So {x}.", "You are saying that {x}.", "I hear that {x}."]).format(x=ech) if ech else None
        if echo_line and echo_line.lower() not in used and rng.random() < 0.75:
            used.add(echo_line.lower())
            parts.append(echo_line)
        elif rng.random() < 0.3:
            n = pick(NORMALISE, True)
            if n:
                parts.append(n)
        safe_q = "Do you feel safe where you are right now?"
        if "fear" in sig and safe_q.lower() not in used and stage in ("open", "explore"):
            parts.append(pick([safe_q]))
        else:
            parts.append(self._question(pick, emo, sig, stage))
        chips = ["Yes, I feel safe", "No, I feel unsafe", "Not sure"] if "fear" in sig and parts[-1].startswith("Do you feel safe") else None
        return " ".join(parts[:3]), chips

    @staticmethod
    def _acks(emo, sig, inten, rng):
        topic = [a for s in sig if s in TOPIC_ACK for a in TOPIC_ACK[s]]
        pool = list(ACK.get(emo, ACK["stress"]))
        if inten >= 7:
            pool += HIGH_ACK * 2
        if topic:
            pool = topic * 2 + pool if rng.random() < 0.6 else pool + topic
        return pool

    PRIORITY = ["fear", "trauma_memory", "case_stress", "shame_guilt", "relationship", "sleep_problem", "academic_stress", "work_stress"]

    @classmethod
    def _question(cls, pick, emo, sig, stage):
        st = "explore" if stage == "open" else stage
        tiers = []
        for s in sorted(sig, key=lambda x: cls.PRIORITY.index(x) if x in cls.PRIORITY else 99):
            tiers.append(Q_TOPIC.get(s, {}).get(st))
        tiers.append(Q_EMO.get(emo, {}).get(st))
        tiers.append(Q_GENERIC[st])
        tiers += [Q_GENERIC[k] for k in ("feel", "explore", "help") if k != st]    # last resort: questions from other stages
        for t in tiers:
            if t:
                q = pick(t, True)
                if q:
                    return q
        return pick(Q_GENERIC[st])

    @staticmethod
    def _tip_reply(pick, tips, lead):
        tip = _lower(pick(tips))
        check = pick(TIP_CHECKS, True)
        return " ".join(x for x in (lead, pick(TIP_LEADS).format(t=tip), check) if x)

    @staticmethod
    def _close(pick, tips):
        return f"{pick(CLOSE_1)} One small thing that may help: {_lower(pick(tips))} {pick(CLOSE_3)}"
