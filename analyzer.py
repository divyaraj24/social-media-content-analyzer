"""
Engagement analysis engine.

Deliberately rule-based (no external AI API / key required) so the
app works fully offline and deterministically. Scores content on a
handful of well-known social-media-engagement heuristics and returns
concrete, actionable suggestions.
"""
import re

HASHTAG_RE = re.compile(r"#\w+")
MENTION_RE = re.compile(r"@\w+")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs, emoticons, transport, supplemental
    "\U00002600-\U000027BF"  # misc symbols & dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\U00002B00-\U00002BFF"  # misc symbols/arrows, e.g. ⭐ ⬛ ⬜
    "\U00002300-\U000023FF"  # misc technical, e.g. ⌚ ⏰ ⏳
    "\U0000203C\U00002049"  # ‼ ⁉
    "\U0000FE0F\U0000200D"  # variation selector-16 + ZWJ, bind combined sequences
    "]+"
)

CTA_PHRASES = [
    "comment below", "let us know", "tag a friend", "tag someone",
    "share this", "drop a", "click the link", "link in bio", "swipe up",
    "dm us", "follow us", "subscribe", "sign up", "learn more",
    "check it out", "read more", "shop now", "get yours", "join us",
    "what do you think", "tell us",
]

IDEAL_WORD_RANGE = (40, 80)   # sweet spot for most platforms
IDEAL_HASHTAG_RANGE = (3, 8)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def analyze_content(text: str) -> dict:
    words = _word_count(text)
    hashtags = HASHTAG_RE.findall(text)
    mentions = MENTION_RE.findall(text)
    urls = URL_RE.findall(text)
    emojis = EMOJI_RE.findall(text)
    emoji_count = sum(len(e) for e in emojis)
    has_question = "?" in text
    lower_text = text.lower()
    cta_hits = [p for p in CTA_PHRASES if p in lower_text]

    suggestions = []
    score = 100

    # --- Length ---
    lo, hi = IDEAL_WORD_RANGE
    if words < lo:
        score -= 15
        suggestions.append({
            "category": "Length",
            "severity": "medium",
            "message": (
                f"Your post is quite short ({words} words). Posts in the "
                f"{lo}-{hi} word range tend to get more engagement — "
                "consider adding context, a story hook, or more detail."
            ),
        })
    elif words > hi * 2:
        score -= 10
        suggestions.append({
            "category": "Length",
            "severity": "low",
            "message": (
                f"Your post is quite long ({words} words). Consider "
                "tightening it up so readers don't drop off before the CTA."
            ),
        })
    else:
        suggestions.append({
            "category": "Length",
            "severity": "good",
            "message": f"Good length ({words} words) — easy to read in one glance.",
        })

    # --- Hashtags ---
    h_lo, h_hi = IDEAL_HASHTAG_RANGE
    if len(hashtags) == 0:
        score -= 15
        suggestions.append({
            "category": "Hashtags",
            "severity": "high",
            "message": "No hashtags found. Adding 3-8 relevant hashtags "
                        "significantly improves discoverability.",
        })
    elif len(hashtags) < h_lo:
        score -= 5
        suggestions.append({
            "category": "Hashtags",
            "severity": "low",
            "message": f"Only {len(hashtags)} hashtag(s) used. Try adding "
                        f"a few more (aim for {h_lo}-{h_hi}) to widen reach.",
        })
    elif len(hashtags) > h_hi:
        score -= 10
        suggestions.append({
            "category": "Hashtags",
            "severity": "medium",
            "message": f"{len(hashtags)} hashtags is a lot — it can look "
                       "spammy. Trim to your {h_hi} most relevant ones.".format(h_hi=h_hi),
        })
    else:
        suggestions.append({
            "category": "Hashtags",
            "severity": "good",
            "message": f"Solid hashtag usage ({len(hashtags)}).",
        })

    # --- Call to action ---
    if not cta_hits:
        score -= 15
        suggestions.append({
            "category": "Call to Action",
            "severity": "high",
            "message": "No clear call-to-action detected. Ask a question "
                        "or invite comments/shares to boost engagement "
                        "(e.g. 'What do you think?', 'Tag a friend').",
        })
    else:
        suggestions.append({
            "category": "Call to Action",
            "severity": "good",
            "message": f"Nice — found a call-to-action ({cta_hits[0]!r}).",
        })

    # --- Question / conversation starter ---
    if not has_question:
        score -= 5
        suggestions.append({
            "category": "Engagement Hook",
            "severity": "low",
            "message": "No question in the post. Questions are one of the "
                        "easiest ways to prompt comments.",
        })

    # --- Emojis ---
    if emoji_count == 0:
        score -= 5
        suggestions.append({
            "category": "Visual Appeal",
            "severity": "low",
            "message": "No emojis detected. A couple of relevant emojis can "
                        "make posts feel warmer and break up text visually.",
        })
    elif emoji_count > 10:
        score -= 5
        suggestions.append({
            "category": "Visual Appeal",
            "severity": "medium",
            "message": "Quite a lot of emojis — consider trimming to keep "
                       "the message clear and professional.",
        })
    else:
        suggestions.append({
            "category": "Visual Appeal",
            "severity": "good",
            "message": f"Good use of emojis ({emoji_count}).",
        })

    # --- Links ---
    if urls:
        suggestions.append({
            "category": "Links",
            "severity": "good",
            "message": f"{len(urls)} link(s) found — make sure they're "
                        "tracked/shortened if you want click analytics.",
        })

    score = max(0, min(100, score))

    return {
        "engagement_score": score,
        "stats": {
            "word_count": words,
            "hashtag_count": len(hashtags),
            "mention_count": len(mentions),
            "url_count": len(urls),
            "emoji_count": emoji_count,
            "has_question": has_question,
            "has_call_to_action": bool(cta_hits),
        },
        "suggestions": suggestions,
    }
