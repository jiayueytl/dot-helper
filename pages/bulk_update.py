import streamlit as st
import pandas as pd
import random
import math

from config import COMPLETED_STATUS, QA_DONE_STATUS
from utils.api import (
    get_pipeline_runs,
    get_dataset_records,
    bulk_update_qa,
    get_users_with_roles,
)
from utils.data_processing import get_performance_tier

# =====================================================
#  HELPERS
# =====================================================

def safe_df(raw):
    """Convert any API response into a valid DataFrame."""
    if raw is None:
        return pd.DataFrame()
    if isinstance(raw, pd.DataFrame):
        return raw
    if isinstance(raw, list):
        if len(raw) > 0 and isinstance(raw[0], dict):
            return pd.DataFrame(raw)
        return pd.DataFrame({"value": raw})
    if isinstance(raw, dict):
        for key in ["records", "data", "items"]:
            if key in raw and isinstance(raw[key], list):
                return safe_df(raw[key])
        if all(not isinstance(v, (list, dict)) for v in raw.values()):
            return pd.DataFrame([raw])
        try:
            return pd.json_normalize(raw)
        except:
            return pd.DataFrame()
    return pd.DataFrame({"value": [raw]})


def sample_for_qa(df, rate, seed=42):
    """Select completed items per annotator/project/dataset."""
    result = {}
    rng = random.Random(seed)
    df = df[df['assignee_name']!="Unknown"]
    for (user, ds), group in df.groupby(["assignee_name", "dataset_name"]):
        completed = group[group["status"].str.lower().isin(COMPLETED_STATUS)]
        completed = completed[~completed["status"].str.lower().isin(QA_DONE_STATUS)]
        # completed = group[~group["assignee_name"].str.lower().isin(["unknown"])]
        qids = completed["id"].dropna().astype(str).unique().tolist()
        if not qids:
            continue

        sample_size = min(len(qids), math.ceil(len(qids) * rate / 100))
        rng.shuffle(qids)
        result[f"{user}||{ds}"] = qids[:sample_size]

    return result


def flatten_task_pool(selected):
    pool = []
    for key, qids in selected.items():
        for q in qids:
            pool.append((q, key))
    return pool


def distribute(pool, qa_list):
    """Assign items proportionally based on capacity."""
    if not qa_list or not pool:
        return {}

    random.shuffle(pool)
    total_cap = sum(cap for _, cap in qa_list)
    total_tasks = len(pool)
    assignments = {qa: [] for qa, _ in qa_list}

    # Proportional allocation
    proportional = {qa: math.floor((cap / total_cap) * total_tasks) for qa, cap in qa_list}
    idx = 0
    for qa, target in proportional.items():
        for _ in range(target):
            if idx >= total_tasks: break
            assignments[qa].append(pool[idx][0])
            idx += 1

    # Round-robin leftovers
    remaining = {qa: cap - len(assignments[qa]) for qa, cap in qa_list}
    qa_cycle = [qa for qa, cap in qa_list if remaining[qa] > 0]
    cycle_i = 0
    while idx < total_tasks and qa_cycle:
        qa = qa_cycle[cycle_i % len(qa_cycle)]
        assignments[qa].append(pool[idx][0])
        remaining[qa] -= 1
        idx += 1
        qa_cycle = [q for q in qa_cycle if remaining[q] > 0]
        cycle_i += 1

    return assignments


def process_records_to_report(df):
    report_rows = []
    for (assignee_name, dataset_name), group in df.groupby(["assignee_name", "dataset_name"]):
        total = len(group)
        completed = len(group[group["status"].str.lower().isin(COMPLETED_STATUS)])
        comp_rate = round((completed / total) * 100, 2) if total else 0

        ready_for_qa = len(group[group["status"].str.lower() == "ready_for_qa"])
        selected_qa_rate = round((ready_for_qa / completed) * 100, 2) if completed else 0

        qa_completed = len(group[group["status"].str.lower().isin(QA_DONE_STATUS)])
        qa_comp_rate = round((qa_completed / completed) * 100, 2) if completed else 0

        qa_p = len(group[group["qa_flag"].str.lower() == "pass"])
        qa_f = len(group[group["qa_flag"].str.lower() == "fail"])
        qa_pass_rate = round((qa_p / qa_completed) * 100, 2) if qa_completed else 0

        report_rows.append({
            "assignee_name": assignee_name or "Unassigned",
            "dataset_name": dataset_name or "Unknown Dataset",
            "total_assigned": total,
            "total_completed": completed,
            "comp_rate": comp_rate,
            "ready_for_qa": ready_for_qa,
            "selected_qa_rate": selected_qa_rate,
            "total_qa": qa_completed,
            "qa_comp_rate": qa_comp_rate,
            "qa_pass": qa_p,
            "qa_fail": qa_f,
            "qa_pass_rate": qa_pass_rate,
            "performance_tier": get_performance_tier(qa_pass_rate)
        })
    if not report_rows:
        st.warning("No valid data found.")
        return pd.DataFrame()
    return pd.DataFrame(report_rows)


def assignments_to_df(assignments, selected, users_map):
    rows = []
    qid_to_info = {}
    for key, qids in selected.items():
        assignee, dataset = key.split("||")
        for qid in qids:
            qid_to_info[qid] = {"assignee_name": assignee, "dataset_name": dataset}

    for qa_user_id, qids in assignments.items():
        qa_name = next((u for u, meta in users_map.items() if meta.get("id") == qa_user_id), qa_user_id)
        grouped = {}
        for qid in qids:
            info = qid_to_info.get(qid)
            if not info: continue
            key = (info["assignee_name"], info["dataset_name"])
            grouped[key] = grouped.get(key, 0) + 1
        for (assignee, dataset), count in grouped.items():
            rows.append({
                "qa_name": qa_name,
                "assignee_name": assignee,
                "dataset_name": dataset,
                "assigned_qa_question_count": count
            })
    return pd.DataFrame(rows)


# =====================================================
#  MAIN PAGE
# =====================================================

def bulk_update_page():
    st.title("🔍 Bulk QA Assigner")

    # --- Initialize session state ---
    for key in ["pipeline_runs", "records_df", "selected", "assignments"]:
        if key not in st.session_state:
            st.session_state[key] = None if key != "selected" and key != "assignments" else {}

    # --- 1) Load QAs ---
    users = get_users_with_roles()
    qa_users = [u for u, meta in users.items() if any("QA" in r.upper() for r in meta["roles"])]

    # --- 2) Pipeline runs ---
    if st.button("Load pipeline runs"):
        with st.spinner("Loading..."):
            try:
                data = get_pipeline_runs()
                st.session_state["pipeline_runs"] = [x for x in data if isinstance(x, dict)] if isinstance(data, list) else []
            except Exception as e:
                st.error(f"Error loading runs: {e}")
                st.session_state["pipeline_runs"] = []

    runs = st.session_state.get("pipeline_runs") or []
    if runs:
        selected_run_indices = st.multiselect(
            "Choose pipeline run(s):",
            options=list(range(len(runs))),
            format_func=lambda i: f"{runs[i].get('run_name', 'Unnamed')} ({runs[i].get('id', 'No ID')})"
        )
        selected_run_ids = [str(runs[i].get("id")) for i in selected_run_indices]
    else:
        st.info("Click 'Load pipeline runs' first.")
        selected_run_ids = []

    # --- 3) Fetch records ---
    if st.button("Fetch dataset records") and selected_run_ids:
        with st.spinner("Fetching records..."):
            raw = get_dataset_records(selected_run_ids)
            st.session_state["records_df"] = safe_df(raw)

    df = st.session_state.get("records_df")
    if df is None or df.empty:
        st.info("No records yet. Click above to fetch.")
        st.stop()
    st.success(f"Loaded {len(df)} records.")

    # --- 4) Summary ---
    st.subheader("Summary")
    report = process_records_to_report(df)
    if not report.empty:
        st.dataframe(report, use_container_width=True)

    # --- 5) Sampling ---
    st.subheader("Sampling")
    rate = st.slider("Sample rate (%)", 1, 100, 20)
    if st.button("Select QA samples"):
        st.session_state["selected"] = sample_for_qa(df, rate)

    selected = st.session_state.get("selected", {})
    if selected:
        st.write({k: len(v) for k, v in selected.items()})

    # --- 6) Assign QAs ---
    st.subheader("Assign QA Reviewers")
    chosen_qas = st.multiselect("Choose QA reviewers:", qa_users)
    qa_caps = {}
    cols = st.columns(3)
    for idx, u in enumerate(chosen_qas):
        with cols[idx % 3]:
            qa_caps[u] = st.number_input(f"{u} capacity", min_value=0, max_value=9999, value=50, key=f"cap_{u}")
    qa_list = [(users[u]["id"], cap) for u, cap in qa_caps.items()]

    if st.button("Distribute"):
        pool = flatten_task_pool(selected)
        st.session_state["assignments"] = distribute(pool, qa_list)
        st.success("Distribution complete.")
        st.json({qa: len(qs) for qa, qs in st.session_state["assignments"].items()})

    # --- 7) Review assignments ---
    st.subheader("Assignments")
    assignments = st.session_state.get("assignments", {})
    df_assignments = assignments_to_df(assignments, selected, users)
    if not df_assignments.empty:
        st.dataframe(df_assignments)
        st.dataframe(df_assignments.groupby('qa_name').agg({"assigned_qa_question_count": "sum"}).reset_index())

    # --- 8) Execute bulk update ---
    if st.checkbox("Confirm bulk update") and st.button("Run now"):
        results = []
        with st.spinner("Sending bulk updates..."):
            for run_id in selected_run_ids:
                for qa_user_id, qids in assignments.items():
                    try:
                        ok, msg = bulk_update_qa(run_id, qids, qa_user_id, "ready_for_qa")
                    except Exception as e:
                        ok, msg = False, f"Exception: {e}"
                    results.append({
                        "pipeline_run_id": run_id,
                        "qa_user_id": qa_user_id,
                        "count": len(qids),
                        "success": ok,
                        "msg": msg
                    })
        st.success("Bulk update completed.")
        st.dataframe(pd.DataFrame(results))
