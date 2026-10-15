"""Inert local consent-review HTML with escaped user/model text."""
from __future__ import annotations
import html
import json
from reference.local_review_lifecycle import ReviewDraft, ReviewError

def render_review_html(review: ReviewDraft) -> str:
    if type(review) is not ReviewDraft:
        raise ReviewError("invalid_review")
    details = review.display()
    def safe(value):
        return html.escape(json.dumps(value, ensure_ascii=True)[1:-1], quote=True)
    target = safe(details["target"])
    service = safe(details["service"])
    operation = safe(details["operation"])
    risk = safe(details["risk"])
    args = html.escape(json.dumps(details["arguments"], ensure_ascii=True,
                                  sort_keys=True, indent=2), quote=True)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>GoreeCloud AI - Review Proposed Action</title></head><body>'
        '<main aria-labelledby="review-title">'
        '<h1 id="review-title">Review proposed action</h1>'
        '<p role="status">Preview only. No approval issued. Execution disabled.</p>'
        '<dl><dt>Service</dt><dd>' + service + '</dd>'
        '<dt>Operation</dt><dd>' + operation + '</dd>'
        '<dt>Target</dt><dd>' + target + '</dd>'
        '<dt>Risk</dt><dd>' + risk + '</dd></dl>'
        '<h2>Proposed data</h2>'
        '<pre role="region" aria-label="Proposed argument values">' + args + '</pre>'
        '<p>Only a separate trusted backend can validate consent.</p>'
        '</main></body></html>'
    )
