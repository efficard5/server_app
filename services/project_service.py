"""
services/project_service.py
──────────────────────────
Logic for project and topic registry management.
"""

import pandas as pd

from services.milestone_service import get_milestone_topic

def build_project_topic_registry(df, milestones, notes, base_projects, base_topics):
    """
    Build a unified list of projects and topics from all data sources.
    Links topics specifically to the projects they belong to.
    Returns: (list of projects, list of topics, registry dict)
    """
    projects_found = set()
    topic_mapping = {}  # project_name -> set of topics

    def add_to_mapping(proj, topic):
        if not proj or pd.isna(proj):
            return
        proj = str(proj).strip()
        if not proj:
            return
        projects_found.add(proj)
        if proj not in topic_mapping:
            topic_mapping[proj] = set()
        if topic and not pd.isna(topic):
            topic = str(topic).strip()
            if topic:
                topic_mapping[proj].add(topic)

    # 1. Extract from tasks (Gantt)
    if not df.empty:
        # DB column is lowercase 'project' and 'topic'
        for _, row in df.iterrows():
            p = row.get("project")
            t = row.get("topic")
            add_to_mapping(p, t)

    # 2. Extract from milestones
    if milestones:
        for mil in milestones.values():
            p = mil.get("project_context")
            # Use service helper to resolve topic
            t = get_milestone_topic(mil)
            add_to_mapping(p, t)
            # Also check internal tasks if they exist
            tasks = mil.get("tasks")
            if isinstance(tasks, dict):
                for t_info in tasks.values():
                    add_to_mapping(p, t_info.get("topic"))

    # 3. Extract from notes
    if notes:
        for p, p_info in notes.items():
            # Structure: {project: {"Topics": {topic_name: note_text}}}
            topics_in_note = p_info.get("Topics", {})
            if topics_in_note:
                for t in topics_in_note:
                    add_to_mapping(p, t)
            else:
                add_to_mapping(p, None)

    # 4. If a project has NO topics found, fallback to BASE_TOPICS
    for p in projects_found:
        if not topic_mapping[p]:
            topic_mapping[p] = set(base_topics)

    # 5. Handle empty state
    if not projects_found:
        projects_found = set(base_projects)
        for p in projects_found:
            topic_mapping[p] = set(base_topics)

    all_projects = sorted(list(projects_found))
    
    # Registry as dict[str, list[str]]
    registry = {p: sorted(list(topic_mapping[p])) for p in all_projects}

    # Global topics list (for filters etc)
    all_topics_global = set(base_topics)
    for ts in topic_mapping.values():
        all_topics_global.update(ts)

    return all_projects, sorted(list(all_topics_global)), registry
