from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RFPSubmissionScope:
    rfp_id: str
    rfp_title: str
    issuing_authority: str
    submission_id: str
    submission_title: str
    response_owner: str


DEFAULT_SCOPES: tuple[RFPSubmissionScope, ...] = (
    RFPSubmissionScope(
        rfp_id="scft-wheelchair-2026",
        rfp_title="Wheelchair and Specialist Seating Service",
        issuing_authority="Sussex Community NHS Foundation Trust",
        submission_id="blatchford-primary-response",
        submission_title="Blatchford Primary Response Set",
        response_owner="Blatchford",
    ),
)


def list_rfp_scopes() -> list[dict[str, Any]]:
    return [asdict(scope) for scope in DEFAULT_SCOPES]


def resolve_scope(rfp_id: str | None = None, submission_id: str | None = None) -> dict[str, Any] | None:
    scopes = list_rfp_scopes()
    if rfp_id is None and submission_id is None:
        return scopes[0] if scopes else None
    for scope in scopes:
        if rfp_id is not None and scope["rfp_id"] != rfp_id:
            continue
        if submission_id is not None and scope["submission_id"] != submission_id:
            continue
        return scope
    return None
