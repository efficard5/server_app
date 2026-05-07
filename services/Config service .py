"""
services/project_service.py
────────────────────────────
Project/topic registry and progress aggregation.
Pure Python logic — no DB calls, no Drive.
Receives DataFrames and dicts already loaded by the calling code.
"""

import os

import pandas as pd


def clean_label(value) -> str:
    text = str(value or "").strip()
    return "" if text.lower() == "nan" else text


def order_topics(topic_values: list, base_topics: list) -> list:
    topic_list = [clean_label(t) for t in topic_values if clean_label(t)]
    preferred_order = {t: i for i, t in enumerate(base_topics)}
    forced_last = {"Container", "Objects"}
    return sorted(
        list(dict.fromkeys(topic_list)),
        key=lambda t: (t in forced_last, preferred_order.get(t, len(preferred_order)), t.lower()),
    )


def _register(project_map: dict, project: str, topic: str = "") -> None:
    project = clean_label(project)
    topic = clean_label(topic)
    if not project:
        return
    project_map.setdefault(project, [])
    if topic and topic not in project_map[project]:
        project_map[project].append(topic)


def build_project_topic_registry(
    data_df: pd.DataFrame,
    milestones: dict | None,
    notes_db: dict | None,
    base_projects: list,
    base_topics: list,
    storage_root: str = "pmo_storage",
) -> tuple[list, list, dict]:
    from services.milestone_service import get_milestone_topic, get_milestone_topic_increases

    project_map: dict = {}
    for bp in base_projects:
        _register(project_map, bp)

    if data_df is not None and not data_df.empty:
        for _, row in data_df.iterrows():
            _register(project_map, row.get("Project", ""), row.get("Topic", ""))

    for mil_info in (milestones or {}).values():
        mp = clean_label(mil_info.get("project_context", ""))
        _register(project_map, mp)
        for tn in get_milestone_topic_increases(mil_info).keys():
            if tn != "All Topics":
                _register(project_map, mp, tn)
        mt = clean_label(get_milestone_topic(mil_info))
        if mt and mt != "All Topics":
            _register(project_map, mp, mt)
        for ti in mil_info.get("tasks", {}).values():
            tp = clean_label(ti.get("project", "")) or mp
            tt = clean_label(ti.get("topic", ""))
            _register(project_map, tp, tt) if tt != "All Topics" else _register(project_map, tp)

    for pname, pinfo in (notes_db or {}).items():
        _register(project_map, clean_label(pname))
        if isinstance(pinfo, dict):
            for tn in (pinfo.get("Topics") or {}).keys():
                _register(project_map, clean_label(pname), tn)

    if os.path.isdir(storage_root):
        for proj in sorted(os.listdir(storage_root)):
            pp = os.path.join(storage_root, proj)
            if not os.path.isdir(pp):
                continue
            _register(project_map, proj)
            for topic in sorted(os.listdir(pp)):
                if os.path.isdir(os.path.join(pp, topic)):
                    _register(project_map, proj, topic)

    ordered_projects = list(dict.fromkeys(base_projects + list(project_map.keys())))
    ordered_map = {p: order_topics(ts, base_topics) for p, ts in project_map.items()}
    all_topics: list = [t for ts in ordered_map.values() for t in ts]
    ordered_topics = order_topics(base_topics + all_topics, base_topics)
    return ordered_projects, ordered_topics, ordered_map


def get_project_topics(
    project_name: str, data_df: pd.DataFrame | None, registry: dict, base_topics: list
) -> list:
    project_name = clean_label(project_name)
    if not project_name:
        return []
    combined = list(registry.get(project_name, []))
    if data_df is not None and not data_df.empty:
        combined += [
            clean_label(t)
            for t in data_df[data_df["Project"] == project_name]["Topic"].dropna().unique()
        ]
    return order_topics(combined, base_topics)


def aggregate_topic_completion(topic_df: pd.DataFrame) -> float:
    if topic_df.empty or "Completion %" not in topic_df.columns:
        return 0.0
    values = pd.to_numeric(topic_df["Completion %"], errors="coerce").dropna()
    if values.empty:
        return 0.0
    base = float(values.max())
    incremental = float(values[values < base].sum())
    return min(100.0, round(base + incremental, 1))


def build_topic_progress_df(task_df: pd.DataFrame, base_topics: list) -> pd.DataFrame:
    if task_df.empty:
        return pd.DataFrame(columns=["Topic", "Completion %"])
    rows = [
        {"Topic": topic, "Completion %": aggregate_topic_completion(tdf)}
        for topic, tdf in task_df.groupby("Topic")
    ]
    tpdf = pd.DataFrame(rows)
    ordered = order_topics(tpdf["Topic"].tolist(), base_topics)
    tpdf["Topic"] = pd.Categorical(tpdf["Topic"], categories=ordered, ordered=True)
    return tpdf.sort_values("Topic").reset_index(drop=True)


def get_project_scope_df(project_name: str, data_df: pd.DataFrame) -> pd.DataFrame:
    if data_df is None or data_df.empty:
        return pd.DataFrame(columns=getattr(data_df, "columns", []))
    return data_df[data_df["Project"] == project_name].copy()