# API Reference

The app exposes two routes. There is no authentication, no rate limiting,
and no versioning — this is a single-purpose local/demo app.

## `GET /`

Serves the frontend (`templates/index.html`). No parameters.

## `POST /api/analyze`

Accepts one uploaded file, extracts its text, and returns an engagement
analysis.

### Request

- Content type: `multipart/form-data`
- Field: `file` — a single PDF, PNG, or JPG/JPEG, up to 10 MB.

```bash
curl -X POST -F "file=@post.png" http://localhost:5000/api/analyze
```

### Success response — `200 OK`

```json
{
  "filename": "post.png",
  "extracted_text": "Check out our new product launch! #excited #newproduct\nWhat do you think?",
  "analysis": {
    "engagement_score": 70,
    "stats": {
      "word_count": 12,
      "hashtag_count": 2,
      "mention_count": 0,
      "url_count": 0,
      "emoji_count": 0,
      "has_question": true,
      "has_call_to_action": false
    },
    "suggestions": [
      {
        "category": "Length",
        "severity": "medium",
        "message": "Your post is quite short (12 words). Posts in the 40-80 word range tend to get more engagement — consider adding context, a story hook, or more detail."
      }
    ]
  }
}
```

Field notes:

| Field | Type | Notes |
|---|---|---|
| `filename` | string | The sanitized (`secure_filename`) name of the upload, echoed back. |
| `extracted_text` | string | Full text pulled from the file. May contain OCR noise for images. |
| `analysis.engagement_score` | int, 0–100 | Starts at 100, deducted per failed heuristic, clamped. |
| `analysis.stats` | object | Raw counts feeding the heuristics — useful for building custom UI. |
| `analysis.suggestions` | array | One entry per heuristic that ran; `severity` is `good \| low \| medium \| high`. |

### Error responses

All errors return `{"error": "<human-readable message>"}`.

| Status | Cause |
|---|---|
| `400` | No `file` part in the request, no file selected, or an unsupported extension (anything other than `.pdf .png .jpg .jpeg`). |
| `413` | File exceeds the 10 MB limit (`MAX_CONTENT_LENGTH`), enforced by Flask/Werkzeug before the route even runs. |
| `422` | A file was accepted and parsed, but no text could be extracted (e.g. a blank image, or a scanned PDF with no OCR layer). |
| `500` | Any unexpected exception during extraction or analysis — the exception message is included for debugging (`Failed to process file: ...`). |

### Notes / gotchas

- Uploaded files are deleted immediately after the request completes (success
  or failure) — nothing is persisted server-side.
- Analysis is purely text-based. If OCR drops characters (it notably cannot
  read emoji glyphs from images — see [limitations.md](limitations.md)),
  those gaps show up directly in `extracted_text` and therefore in the score.
