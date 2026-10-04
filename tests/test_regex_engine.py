import pytest
from services.regex_engine import analyze, violates_output_policy


def test_normal_message_is_safe():
    r = analyze("hello there")
    assert r["risk_level"] == "SAFE" and r["categories"] == []


@pytest.mark.parametrize("text,cat", [
    ("I have been feeling very stressed lately", "stress"),
    ("I feel anxious and my heart is racing", "anxiety"),
    ("I can't sleep at night", "sleep_problem"),
    ("I can\u2019t sleep", "sleep_problem"),
    ("exams are killing me", "academic_stress"),
    ("I feel so lonely", "loneliness"),
])
def test_distress_categories(text, cat):
    r = analyze(text)
    assert cat in r["categories"] and r["risk_level"] == "LOW_CONCERN"


@pytest.mark.parametrize("text,cat,level", [
    ("I want to kill myself", "suicide", "HIGH_CONCERN"),
    ("I wish I was dead", "suicide", "HIGH_CONCERN"),
    ("I keep hurting myself", "self_harm", "HIGH_CONCERN"),
    ("I want to hurt him", "harm_others", "HIGH_CONCERN"),
    ("I'm going to kill myself tonight", "crisis_intent", "CRISIS"),
    ("I feel hopeless", "hopelessness", "MODERATE_CONCERN"),
])
def test_safety_categories(text, cat, level):
    r = analyze(text)
    assert cat in r["categories"] and r["risk_level"] == level
    assert r["matched_patterns"]


def test_idioms_do_not_trigger():
    assert analyze("I'm going to kill this exam")["risk_level"] != "HIGH_CONCERN"


def test_output_policy():
    assert violates_output_policy("You have depression.")
    assert violates_output_policy("You should take antidepressants.")
    assert not violates_output_policy("Try slowly breathing in for 4 and out for 6.")
