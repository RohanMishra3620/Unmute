"""Deterministic keyword + safety layer. Runs first on every message."""
import re

RISK_LEVELS = ["SAFE", "LOW_CONCERN", "MODERATE_CONCERN", "HIGH_CONCERN", "CRISIS"]


def max_risk(*levels):
    return max(levels, key=RISK_LEVELS.index)


PATTERNS = {
    # --- emotional signals ---
    "anxiety": [r"\banxi(ous|ety)\b", r"\bpanic(king| attacks?)?\b", r"\bworr(y|ied|ying|ies)\b", r"\bnervous\b",
                r"\bon edge\b", r"\b(scared|afraid|terrified)\b", r"\bheart (is |was )?(racing|pounding)\b",
                r"\bcan'?t (breathe|calm down|relax)\b"],
    "overthinking": [r"\boverthink(ing)?\b", r"\bcan'?t (stop|switch off|turn off) (thinking|my (mind|thoughts))\b",
                     r"\bracing thoughts\b", r"\b(thoughts|mind) (keep|won'?t stop|is racing)\b", r"\bwhat if\b"],
    "stress": [r"\bstress(ed|ful)?\b", r"\bpressure\b", r"\boverwhelm(ed|ing)\b",
               r"\btoo much (to do|going on|on my plate)\b", r"\bcan'?t cope\b"],
    "sadness": [r"\bsad(ness)?\b", r"\bdepress(ed|ing|ion)\b", r"\b(feel(ing)?|been|am|i'?m) (so |very |really )?(down|low|blue|empty|numb)\b",
                r"\bcry(ing)?\b", r"\bunhappy\b", r"\bworthless\b", r"\bheartbroken\b"],
    "loneliness": [r"\blonel(y|iness)\b", r"\b(nobody|no one) (cares|understands|likes|to talk)\b", r"\balone\b",
                   r"\bleft out\b", r"\bno friends\b"],
    "social_isolation": [r"\bisolat(ed|ing)\b", r"\b(avoid|avoiding|withdrawn|withdrawing)\b.{0,20}\b(people|friends|everyone|family|social)\b",
                         r"\bstay(ing)? in my room\b", r"\bdon'?t (want to )?(see|talk to|meet) (anyone|people)\b"],
    "sleep_problem": [r"\b(can'?t|cannot|couldn'?t|unable to|trouble|difficulty|struggl\w+( with| to)?) (to )?sleep(ing)?\b",
                      r"\binsomnia\b", r"\bsleepless\b", r"\bsleep(ing)? (badly|poorly|too much|problems?|issues?)\b",
                      r"\b(awake|up) all night\b", r"\bnightmares?\b", r"\btossing and turning\b"],
    "anger": [r"\b(angry|anger|furious|irritat\w+|frustrat\w+|annoyed|rage)\b", r"\bhate (my|him|her|them|everyone|this)\b",
              r"\bsnap(ped|ping)? at\b"],
    "academic_stress": [r"\b(exams?|finals?|grades?|marks|assignments?|deadlines?|thesis|backlogs?|placements?|cgpa|gpa|results)\b",
                        r"\b(fail(ed|ing)?|failure)\b.{0,20}\b(exam|course|class|subject)\b",
                        r"\b(college|school|university|studies|studying)\b.{0,30}\b(stress|pressure|hard|tough|burden|overwhelm)\w*\b"],
    "work_stress": [r"\b(workload|boss|manager|coworkers?|colleagues?|layoffs?|fired|unemployed|office politics)\b",
                    r"\b(work|job|office)\b.{0,30}\b(stress|pressure|overwhelm|toxic|too much|exhaust)\w*\b",
                    r"\b(stress|pressure|overwhelm)\w*\b.{0,30}\b(work|job|office)\b"],
    "relationship": [r"\b(breakup|break up|broke up|divorce)\b",
                     r"\b(fight|fighting|argu\w+|fought) with (my )?(parents|mom|dad|mother|father|friends?|partner|girlfriend|boyfriend|family|wife|husband|brother|sister)\b",
                     r"\btoxic (relationship|friend|family|partner)\b", r"\bwhat will (people|society|everyone) say\b", r"\blog kya kahenge\b",
                     r"\b(girlfriend|boyfriend|partner|wife|husband)\b.{0,30}\b(left|cheat\w*|ignor\w+|problems?)\b"],
    "low_motivation": [r"\bno (motivation|energy|interest|drive)\b", r"\bunmotivated\b",
                       r"\bcan'?t (focus|concentrate|get (up|started|out of bed))\b", r"\b(lost|losing) interest\b",
                       r"\bprocrastinat\w+\b", r"\bnothing (excites|interests) me\b"],
    "exhaustion": [r"\bexhaust(ed|ion)\b", r"\bburn(ed|t)[- ]?out\b", r"\bdrained\b", r"\bworn out\b",
                   r"\bso tired\b", r"\bfatigue(d)?\b", r"\bemotionally (tired|spent|drained)\b"],
    "case_stress": [r"\b(court|hearing|trial|police station|fir|lawyer|advocate|witness|investigation|compensation|bail|judge|verdict|testify|testimony|cross[- ]examination|legal process)\b",
                    r"\b(my|the|this|our) case\b"],
    "fear": [r"\b(afraid|scared|terrified|frightened) of (him|her|them|that person|everyone|people|going|being|leaving|staying)\b",
             r"\b(fear|frightened|threat(en\w*)?|afraid of|scared of|follow(ed|ing) me|they will (come|find|hurt))\b",
             r"\bfeel(ing)? (unsafe|insecure)\b", r"\bscared to (go|step|leave|sleep|be)\b"],
    "shame_guilt": [r"\b(ashamed|shame|guilty|guilt|my fault|blame myself|blaming myself)\b"],
    "trauma_memory": [r"\bmemor(y|ies)\b.{0,25}\b(come|comes|coming|keep|keeps) back\b", r"\b(flashbacks?|keeps? coming back|can'?t forget|the incident|what happened to me|reliv\w+|bad memories|triggered)\b"],
    # --- non-distress signals (used for the report's positive signals) ---
    "positive": [r"\b(feel(ing)?|am|i'?m|been|getting) (a bit |a little |much |so |really )?(better|happy|hopeful|calm|relieved|grateful|proud|great|good)\b",
                 r"\b(grateful|thankful|looking forward|excited)\b"],
    "help_seeking": [r"\b(need|want|looking for|seeking) (some )?(help|support|advice|someone to talk)\b",
                     r"\btalk(ing)? to (someone|a (counsel|therap)\w+|my (friend|mom|dad|family))\b", r"\bwant to (feel|get) better\b"],
    "coping_used": [r"\b(went|go|going) (for )?(a )?(walk|run|jog)\b", r"\b(meditat|journal|exercis|workout|yoga|pray)\w*\b",
                    r"\b(talked|spoke) (to|with) (a |my )?(friend|mom|dad|family|counsel\w+|therapist)\b", r"\blistening to music\b"],
    # --- safety signals ---
    "hopelessness": [r"\bhopeless(ness)?\b", r"\bno (point|hope|way out|future)\b",
                     r"\bnothing (matters|will (ever )?change|is going to get better)\b",
                     r"\bcan'?t (go on|take (it|this) (any ?more|anymore))\b", r"\bgive up\b", r"\bwhat'?s the point\b", r"\btrapped\b"],
    "suicide": [r"\bsuicid(e|al)\b", r"\bkill(ing)? (myself|my self)\b", r"\bend(ing)? (my (own )?life|it all)\b",
                r"\b(want|wanted|wanna) (to )?(die|be dead|disappear forever)\b", r"\bwish (i|that i) (was|were) (dead|never born)\b",
                r"\bbetter off (dead|without me)\b", r"\bno reason to (live|go on)\b",
                r"\b(don'?t|do not) want to (live|be alive|be here|wake up)\b", r"\b(tired of living|not worth living)\b",
                r"\bfeel(ing)? like dying\b"],
    "self_harm": [r"\b(cut|cutting|hurt|hurting|harm|harming|burn|burning|punish|punishing) (myself|my self)\b",
                  r"\bself[- ]?(harm|injur|mutilat)\w*\b"],
    "harm_others": [r"\b(kill|hurt|harm|stab|shoot|attack|beat up) (him|her|them|someone|somebody|people|everyone)\b",
                    r"\bwant(ed)? to (kill|hurt|harm) (my|our|the) \w+\b", r"\bmake (them|him|her) pay\b"],
    "immediate_danger": [r"\b(i'?m|i am) (in danger|not safe|unsafe)\b",
                         r"\b(he|she|they|someone) (is|are) (hitting|beating|threatening|attacking|abusing) me\b"],
    "crisis_intent": [r"\b(going to|gonna|about to|planning to|plan to|decided to|ready to) (kill myself|end (it all|it|my life)|commit suicide|take my (own )?life|overdose)\b",
                      r"\bsuicide (note|plan)\b",
                      r"\b(have|got|holding) (the |a |some )?(pills|rope|gun|knife|blade|razor)\b.{0,40}\b(ready|now|tonight|with me|in my hand)\b",
                      r"\b(tonight|right now|today)\b.{0,30}\b(kill myself|end my life|end it all)\b",
                      r"\b(kill myself|end my life|end it all)\b.{0,30}\b(tonight|right now|today)\b",
                      r"\btake all (the |my )?(pills|tablets)\b",
                      r"\b(going to|gonna|about to) (kill|hurt|stab|shoot|attack) (him|her|them|someone|somebody|my \w+)\b"],
}

CATEGORY_RISK = {"crisis_intent": "CRISIS", "immediate_danger": "CRISIS", "suicide": "HIGH_CONCERN",
                 "self_harm": "HIGH_CONCERN", "harm_others": "HIGH_CONCERN", "hopelessness": "MODERATE_CONCERN"}
DISTRESS = {"anxiety", "overthinking", "stress", "sadness", "loneliness", "social_isolation", "sleep_problem", "anger",
            "academic_stress", "work_stress", "relationship", "low_motivation", "exhaustion",
            "case_stress", "fear", "shame_guilt", "trauma_memory"}

_COMPILED = {c: [re.compile(p) for p in ps] for c, ps in PATTERNS.items()}


def normalize(text):
    return " ".join(text.lower().replace("\u2019", "'").replace("\u2018", "'").split())


def analyze(text):
    t = normalize(text)
    cats, matched = [], []
    for cat, regexes in _COMPILED.items():
        for rx in regexes:
            m = rx.search(t)
            if m:
                cats.append(cat)
                matched.append({"category": cat, "pattern": rx.pattern, "match": m.group(0)})
                break
    risk = "LOW_CONCERN" if DISTRESS & set(cats) else "SAFE"
    for c in cats:
        risk = max_risk(risk, CATEGORY_RISK.get(c, "SAFE"))
    return {"categories": cats, "matched_patterns": matched, "risk_level": risk}


# Output guard: applied to LLM-written text so it can never diagnose, prescribe or claim to be a clinician.
_BLOCK = [re.compile(p) for p in [
    r"\byou (have|suffer from|are suffering from|seem to have|likely have|probably have) (a |an )?(clinical )?(depression|anxiety disorder|bipolar|ptsd|ocd|adhd|schizophrenia|disorder)",
    r"\bdiagnos(is|ed|e|ing)\b",
    r"\b(take|try|increase|stop|reduce|prescri)\w*\b.{0,25}\b(medication|medicine|antidepressants?|pills|mg|dose|dosage|xanax|valium|sertraline|prozac|benzodiazepines?|melatonin)\b",
    r"\b(i am|i'?m) (a |your )?(therapist|doctor|psychologist|psychiatrist|counsel+or|human)\b",
    r"\bhow to (kill|hurt|harm) yourself\b",
]]


def violates_output_policy(text):
    t = normalize(text)
    return any(rx.search(t) for rx in _BLOCK)
