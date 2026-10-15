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
        '<meta http-equiv="Content-Security-Policy" content="default-src &apos;none&apos;; style-src &apos;unsafe-inline&apos;; form-action &apos;none&apos;; base-uri &apos;none&apos;">'
        '<title>GoreeCloud AI - Review Proposed Action</title>'
        '<style>'
        ':root{color-scheme:light dark;font:16px/1.55 system-ui,sans-serif}'
        'body{max-width:50rem;margin:0 auto;padding:clamp(1rem,4vw,3rem);'
        'background:Canvas;color:CanvasText}'
        'main{padding:clamp(1rem,4vw,2.4rem);border:1px solid GrayText;'
        'border-radius:1.25rem;box-shadow:0 5px 24px #7772}'
        'h1{font-size:clamp(1.5rem,4vw,2rem);line-height:1.2;margin-top:0}'
        'h2{font-size:1.1rem}'
        'p[role=status]{padding:.75rem 1rem;border-inline-start:4px solid'
        ' currentColor;background:color-mix(in srgb,CanvasText 6%,Canvas)}'
        'dl{display:grid;grid-template-columns: minmax(7rem, 1fr) 3fr;gap:.5rem 1rem}'
        'dt{font-weight:650}dd{margin:0;overflow-wrap:anywhere}'
        'pre{max-height:20rem;overflow:auto;padding:1rem;white-space:pre-wrap;'
        'overflow-wrap:anywhere;border:1px solid GrayText;border-radius:.65rem}'
        '@media(max-width:32rem){dl{display:block}dt{margin-top:.65rem}}'
        '@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}'
        '</style></head><body>'
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
