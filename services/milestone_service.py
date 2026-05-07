"""
services/milestone_service.py
──────────────────────────────
Milestone business logic — reads/writes PostgreSQL via milestone_repo.
"""

from db.repositories.milestone_repo import (
    get_all_milestones,
    save_milestone,
    delete_milestone,
    save_all_milestones,
)


def load_planned_milestones() -> dict:
    return get_all_milestones()


def save_planned_milestones(milestones: dict) -> None:
    """Save all milestones (full replace)."""
    save_all_milestones(milestones)


def save_single_milestone(milestone_id: str, mil_info: dict) -> None:
    """Save one milestone without touching others."""
    save_milestone(milestone_id, mil_info)


def remove_milestone(milestone_id: str) -> None:
    delete_milestone(milestone_id)


# ── Business helpers (pure logic — no DB calls) ───────────────────────────────

def get_milestone_topic(mil_info: dict) -> str:
    explicit = str(mil_info.get("topic", "")).strip()
    if explicit:
        return explicit
    task_topics = {
        str(t.get("topic", "")).strip()
        for t in mil_info.get("tasks", {}).values()
        if str(t.get("topic", "")).strip()
    }
    if not task_topics:
        return ""
    if "All Topics" in task_topics or len(task_topics) > 1:
        return "All Topics"
    return next(iter(task_topics))


def get_milestone_progress(mil_info: dict) -> float:
    pi = mil_info.get("progress_increase", 0)
    if isinstance(pi, dict):
        return sum(float(v or 0) for v in pi.values())
    return float(pi or 0)


def get_milestone_topic_increases(mil_info: dict) -> dict:
    pi = mil_info.get("progress_increase", 0)
    if isinstance(pi, dict):
        return {k: float(v or 0) for k, v in pi.items()}
    topic = get_milestone_topic(mil_info)
    val = float(pi or 0)
    if topic and topic != "" and val > 0:
        return {topic: val}
    return {}


def get_completed_milestone_total(
    project_name: str, milestones: dict, topic_name: str = "All Topics"
) -> float:
    total = 0.0
    if not str(project_name).strip():
        return total
    for mil_info in milestones.values():
        if not bool(mil_info.get("completed", False)):
            continue
        if str(mil_info.get("project_context", "")).strip() != str(project_name).strip():
            continue
        milestone_topic = get_milestone_topic(mil_info)
        if topic_name != "All Topics" and milestone_topic not in [topic_name, "All Topics"]:
            continue
        total += get_milestone_progress(mil_info)
    return total


def get_planned_topic_adjustments(
    project_name: str, milestones: dict, base_topics: list
) -> dict:
    adjustments: dict = {}
    if not project_name:
        return adjustments
    clean_target = str(project_name).strip()
    for mil_info in milestones.values():
        milestone_project = str(mil_info.get("project_context", "")).strip()
        if milestone_project != clean_target:
            if milestone_project not in clean_target and clean_target not in milestone_project:
                continue
        if not mil_info.get("completed", False):
            continue
        for topic, increase in get_milestone_topic_increases(mil_info).items():
            if increase <= 0:
                continue
            if topic == "All Topics":
                for pt in base_topics:
                    adjustments[pt] = adjustments.get(pt, 0.0) + float(increase)
            else:
                adjustments[topic] = adjustments.get(topic, 0.0) + float(increase)
    return adjustments