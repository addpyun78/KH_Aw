from __future__ import annotations

from typing import Any

from .util import utc_now


STAGE_DEPENDENCIES = {
    "intake": [],
    "analyze": ["intake"],
    "research": ["analyze"],
    "design": ["research"],
    "implement": ["design"],
    "review": ["implement"],
    "test": ["review"],
    "release": ["test"],
}


def build_task_graph(requirements: dict[str, Any]) -> dict[str, Any]:
    tickets = []
    previous_by_stage: dict[str, str] = {}
    for index, requirement in enumerate(requirements.get("requirements", []), 1):
        ticket_id = f"TICKET-{index:04d}"
        classes = set(requirement.get("classifications", []))
        if "research" in classes:
            stage, role = "research", "researcher"
        elif "testing" in classes or "evidence" in classes:
            stage, role = "test", "verifier"
        elif "installation" in classes or "deliverable" in classes:
            stage, role = "release", "release-engineer"
        elif "recovery" in classes:
            stage, role = "implement", "repair-engineer"
        else:
            stage, role = "implement", "implementer"
        previous = previous_by_stage.get(stage, "")
        tickets.append({
            "id": ticket_id,
            "requirementIds": [requirement["id"]],
            "stage": stage,
            "role": role,
            "dependencies": [previous] if previous else [],
            "inputs": [requirement["source"]],
            "allowedScope": [],
            "requiredOutputs": [],
            "outputs": [],
            "verification": [],
            "retry": {"maxSameStrategy": 1, "changeStrategyOnRepeat": True},
            "retryHistory": [],
            "status": "pending",
        })
        requirement.setdefault("implementationTickets", []).append(ticket_id)
        previous_by_stage[stage] = ticket_id
    return {
        "schemaVersion": "4.0",
        "generatedAt": utc_now(),
        "stageDependencies": STAGE_DEPENDENCIES,
        "tickets": tickets,
    }
