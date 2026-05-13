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
        
        milestone_is_done = bool(mil_info.get("completed", False))
        m_tasks = mil_info.get("tasks", {})
        m_errors = mil_info.get("milestone_errors", {})
        topic_inc = get_milestone_topic_increases(mil_info)
        
        for t_name, total_increase in topic_inc.items():
            if total_increase <= 0:
                continue
            
            # 1. Identify relevant tasks for this topic
            relevant_task_ids = []
            if t_name == "All Topics":
                relevant_task_ids = list(m_tasks.keys())
            else:
                relevant_task_ids = [tid for tid, t in m_tasks.items() if t.get("topic") == t_name]
            
            # 2. Identify unique errors linked to these tasks
            relevant_error_ids = set()
            for eid, einfo in m_errors.items():
                task_ids_for_error = einfo.get("task_ids", [])
                # If error is linked to ANY of the relevant tasks, it counts for this topic
                if any(tid in relevant_task_ids for tid in task_ids_for_error):
                    relevant_error_ids.add(eid)
                # Special case: If topic is "All Topics", all errors count? 
                # (handled by relevant_task_ids containing all keys)
            
            # 3. Calculate actual increase for this topic
            actual_increase = 0.0
            total_items = len(relevant_task_ids) + len(relevant_error_ids)
            
            if total_items > 0:
                # Sum partial progress for tasks (0-100%)
                task_progress_sum = 0.0
                for tid in relevant_task_ids:
                    t_info = m_tasks[tid]
                    # Use completion_pct if available, fallback to 100 if completed is True
                    pct = float(t_info.get("completion_pct", 100.0 if t_info.get("completed", False) else 0.0))
                    task_progress_sum += (pct / 100.0)
                
                completed_errors = sum(1 for eid in relevant_error_ids if m_errors[eid].get("completed", False))
                
                actual_increase = ((task_progress_sum + completed_errors) / total_items) * float(total_increase)
            else:
                # Fallback to milestone overall completion if no specific tasks or errors
                if milestone_is_done:
                    actual_increase = float(total_increase)
            
            # Apply to adjustments dict
            if t_name == "All Topics":
                for pt in base_topics:
                    adjustments[pt] = adjustments.get(pt, 0.0) + actual_increase
            else:
                adjustments[t_name] = adjustments.get(t_name, 0.0) + actual_increase
                
    return adjustments