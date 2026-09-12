from __future__ import annotations
from difflib import SequenceMatcher
from .schemas import Issue, Review

def _similar(a,b):
    return SequenceMatcher(None,a.lower(),b.lower()).ratio()

def build_issue_ledger(reviews: list[Review], threshold: float=.72, seed_issues: list[Issue] | None=None) -> list[Issue]:
    ledger=[x.model_copy(deep=True) for x in (seed_issues or [])]
    for review in reviews:
        for raw in review.issues:
            raw.raised_by = sorted(set(raw.raised_by + [review.judge_type]))
            hit=None
            for old in ledger:
                same_cat = old.category == raw.category
                if same_cat and _similar(old.summary, raw.summary) >= threshold:
                    hit=old; break
            if hit:
                hit.raised_by=sorted(set(hit.raised_by+raw.raised_by))
                hit.question_refs=sorted(set(hit.question_refs+raw.question_refs))
                hit.evidence.extend(raw.evidence)
                hit.origin=sorted(set(hit.origin+raw.origin))
                rank={'minor':0,'moderate':1,'serious':2,'fatal':3}
                if rank[raw.severity] > rank[hit.severity]: hit.severity=raw.severity
                if raw.detail not in hit.detail: hit.detail += '\n\nCorroborating review: '+raw.detail
            else:
                ledger.append(raw.model_copy(deep=True))
    rank={'fatal':0,'serious':1,'moderate':2,'minor':3}
    ledger.sort(key=lambda x:(rank[x.severity], x.category, x.summary))
    for i, issue in enumerate(ledger,1): issue.id=f'ISS-{i:03d}'
    return ledger
