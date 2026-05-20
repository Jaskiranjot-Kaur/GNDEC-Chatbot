import json
import re
from datetime import datetime
from pathlib import Path

from config import GNDEC


REQUEST_STORE = Path(__file__).resolve().parent.parent / "data" / "request_store.json"

DEFAULT_LINK = GNDEC.get("academic_portal") or GNDEC.get("home")

REQUEST_ROUTING = {
    "bonafide certificate": {
        "office": "Student Section",
        "route": "Bonafide requests are usually reviewed through the student records and administrative support flow.",
        "link": GNDEC.get("academic_portal") or DEFAULT_LINK,
        "title": "Bonafide Support",
    },
    "character certificate": {
        "office": "Administrative Office",
        "route": "Character certificate requests generally move through the administrative records desk for approval.",
        "link": GNDEC.get("academic_portal") or DEFAULT_LINK,
        "title": "Character Certificate Support",
    },
    "transcript approval": {
        "office": "Academic Records Cell",
        "route": "Transcript approvals are usually handled through the academic records workflow and document verification process.",
        "link": GNDEC.get("academic_portal") or DEFAULT_LINK,
        "title": "Transcript Approval Support",
    },
    "noc approval": {
        "office": "Administrative Office",
        "route": "NOC requests are usually routed to the administrative office for document checking and approval follow-up.",
        "link": GNDEC.get("academic_portal") or DEFAULT_LINK,
        "title": "NOC Approval Support",
    },
    "branch change request": {
        "office": "Dean Academics",
        "route": "Branch change requests usually require academic review before the final administrative approval stage.",
        "link": GNDEC.get("admission_portal") or DEFAULT_LINK,
        "title": "Branch Change Support",
    },
    "document approval request": {
        "office": "Administrative Office",
        "route": "Digital document approval requests can be followed through the official administrative support route.",
        "link": DEFAULT_LINK,
        "title": "Document Approval Support",
    },
    "approval status follow-up": {
        "office": "Administrative Office",
        "route": "Use your request ID while checking the latest approval movement with the administrative team.",
        "link": DEFAULT_LINK,
        "title": "Approval Status Support",
    },
    "administrator contact": {
        "office": "Administrative Office",
        "route": "Administrative contact support can help you follow up on pending documents and request guidance.",
        "link": DEFAULT_LINK,
        "title": "Administrator Contact",
    },
    "bonafide support": {
        "office": "Student Section",
        "route": "Bonafide support helps students start the certificate approval workflow and follow up digitally.",
        "link": GNDEC.get("academic_portal") or DEFAULT_LINK,
        "title": "Bonafide Support",
    },
    "other document approval": {
        "office": "Administrative Office",
        "route": "Other document approvals are routed to the administrative office for manual review and follow-up.",
        "link": DEFAULT_LINK,
        "title": "Administrative Follow-up",
    },
}

STATUS_FLOW = {
    "Submitted": "Under Review",
    "Under Review": "Approved",
    "Approved": "Approved",
    "Need Admin Action": "Under Review",
}

ADMIN_STATUS_OPTIONS = {"Submitted", "Under Review", "Approved", "Need Admin Action"}


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _ensure_store() -> None:
    REQUEST_STORE.parent.mkdir(parents=True, exist_ok=True)
    if not REQUEST_STORE.exists():
        REQUEST_STORE.write_text("[]", encoding="utf-8")


def _load_store() -> list[dict]:
    _ensure_store()
    try:
        return json.loads(REQUEST_STORE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_store(items: list[dict]) -> None:
    _ensure_store()
    REQUEST_STORE.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _request_id(student_name: str, roll_number: str, request_type: str) -> str:
    seed = "".join(ch for ch in f"{student_name}{roll_number}{request_type}" if ch.isalnum()).upper()
    seed = (seed[:6] or "GNDECX").ljust(6, "X")
    timestamp = datetime.now().strftime("%d%H%M")
    return f"REQ-{seed}-{timestamp}"


def _route_for(request_type: str) -> dict:
    normalized = _clean(request_type).lower()
    if normalized in REQUEST_ROUTING:
        return REQUEST_ROUTING[normalized]
    return REQUEST_ROUTING["other document approval"]


def _summarize_request(item: dict) -> str:
    lines = [
        "## Request Submitted",
        f"Your `{item['request_type']}` request has been saved in the digital request section.",
        "### Request Summary",
        f"- **Request ID:** {item['request_id']}",
        f"- **Student Name:** {item['student_name'] or 'Not provided'}",
        f"- **Roll Number:** {item['roll_number'] or 'Not provided'}",
        f"- **Priority:** {item['priority']}",
        f"- **Current Status:** {item['status']}",
        f"- **Assigned Office:** {item['office']}",
    ]

    if item.get("reason"):
        lines.append(f"- **Reason:** {item['reason']}")

    lines.extend([
        "### What Happens Next",
        f"- {item['route']}",
        "- Keep the request ID handy while checking approval status.",
        "- Use the official support link below for the latest office route and follow-up.",
    ])
    return "\n".join(lines)


def _history_item(item: dict) -> dict:
    return {
        "request_id": item["request_id"],
        "student_name": item.get("student_name", ""),
        "roll_number": item.get("roll_number", ""),
        "request_type": item["request_type"],
        "priority": item["priority"],
        "reason": item.get("reason", ""),
        "status": item["status"],
        "office": item["office"],
        "created_at": item["created_at"],
        "admin_note": item.get("admin_note", ""),
        "updated_at": item.get("updated_at", ""),
    }


def build_request_response(payload: dict) -> dict:
    student_name = _clean(payload.get("student_name"))
    roll_number = _clean(payload.get("roll_number"))
    request_type = _clean(payload.get("request_type")) or "Document Approval Request"
    priority = _clean(payload.get("priority")) or "Normal"
    reason = _clean(payload.get("reason"))

    request_id = _request_id(student_name, roll_number, request_type)
    route = _route_for(request_type)

    item = {
        "request_id": request_id,
        "student_name": student_name,
        "roll_number": roll_number,
        "request_type": request_type,
        "priority": priority,
        "reason": reason,
        "status": "Submitted",
        "office": route["office"],
        "route": route["route"],
        "created_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "admin_note": "",
    }

    store = _load_store()
    store.append(item)
    _save_store(store)

    return {
        "reply": _summarize_request(item),
        "type": "request",
        "request": _history_item(item),
        "meta": {
            "title": route["title"],
            "link": route["link"],
            "kind": "url",
            "open_label": "Open Official Support",
            "auto_open": False,
        },
    }


def get_request_history(limit: int = 8) -> list[dict]:
    store = _load_store()
    recent = list(reversed(store[-limit:]))
    return [_history_item(item) for item in recent]


def get_admin_requests() -> dict:
    store = list(reversed(_load_store()))
    items = [_history_item(item) for item in store]
    stats = {
        "total": len(items),
        "submitted": sum(1 for item in items if item["status"] == "Submitted"),
        "under_review": sum(1 for item in items if item["status"] == "Under Review"),
        "approved": sum(1 for item in items if item["status"] == "Approved"),
        "need_admin_action": sum(1 for item in items if item["status"] == "Need Admin Action"),
    }
    return {"requests": items, "stats": stats}


def update_request_status(request_id: str) -> dict:
    request_id = _clean(request_id)
    if not request_id:
        raise ValueError("Missing request ID.")

    store = _load_store()
    for item in reversed(store):
        if item.get("request_id") != request_id:
            continue

        current = item.get("status", "Submitted")
        item["status"] = STATUS_FLOW.get(current, "Under Review")
        item["updated_at"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
        _save_store(store)

        return {
            "reply": "\n".join([
                "## Status Updated",
                f"`{item['request_type']}` is now marked as **{item['status']}**.",
                "### Request Details",
                f"- **Request ID:** {item['request_id']}",
                f"- **Assigned Office:** {item['office']}",
                f"- **Last Updated:** {item['updated_at']}",
            ]),
            "type": "request",
            "request": _history_item(item),
            "meta": {
                "title": "Request Status Support",
                "link": _route_for(item["request_type"])["link"],
                "kind": "url",
                "open_label": "Open Official Support",
                "auto_open": False,
            },
        }

    raise ValueError("Request not found.")


def admin_update_request(request_id: str, status: str, admin_note: str = "") -> dict:
    request_id = _clean(request_id)
    status = _clean(status)
    admin_note = _clean(admin_note)

    if not request_id:
        raise ValueError("Missing request ID.")
    if status not in ADMIN_STATUS_OPTIONS:
        raise ValueError("Invalid status selected.")

    store = _load_store()
    for item in reversed(store):
        if item.get("request_id") != request_id:
            continue

        item["status"] = status
        item["admin_note"] = admin_note
        item["updated_at"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
        _save_store(store)

        return {
            "message": "Request updated successfully.",
            "request": _history_item(item),
            "stats": get_admin_requests()["stats"],
        }

    raise ValueError("Request not found.")
