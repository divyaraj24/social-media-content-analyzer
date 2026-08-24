import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer import analyze_content


def test_detects_hashtags():
    result = analyze_content("Great day! #sunshine #happy #life")
    assert result["stats"]["hashtag_count"] == 3


def test_detects_call_to_action():
    result = analyze_content("Check this out. Comment below what you think!")
    assert result["stats"]["has_call_to_action"] is True


def test_detects_question():
    result = analyze_content("Would you try this?")
    assert result["stats"]["has_question"] is True


def test_score_within_bounds():
    result = analyze_content("Just a plain post with nothing special.")
    assert 0 <= result["engagement_score"] <= 100


def test_no_hashtags_flagged():
    result = analyze_content("A post without any tags at all here today.")
    categories = [s["category"] for s in result["suggestions"]]
    assert "Hashtags" in categories
