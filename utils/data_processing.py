import pandas as pd
import zipfile
import io

def csv_to_json_zip(df: pd.DataFrame) -> io.BytesIO:
    """Convert DataFrame to zipped JSON."""
    json_data = df.to_json(orient='records')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.json", json_data)
    zip_buffer.seek(0)
    return zip_buffer

def filter_undone_questions(data):
    """Return items where status != completed."""
    return [d for d in data if d.get("status") != "completed"]

def assign_questions_by_capacity(questions, capacity_df):
    """Distribute questions according to user capacity."""
    if not questions or capacity_df.empty:
        return questions
    capacity_map = {row.user_id: row.capacity for _, row in capacity_df.iterrows()}
    user_load = {u: 0 for u in capacity_map}
    assigned = []
    for q in questions:
        available = [u for u, cap in capacity_map.items() if user_load[u] < cap]
        if not available: break
        chosen = min(available, key=lambda u: user_load[u])
        q["assignee_id"] = chosen
        user_load[chosen] += 1
        assigned.append(q)
    return assigned

def get_performance_tier(pass_rate):
    """Assigns a performance tier based on the QA pass rate."""
    if pass_rate >= 90:
        return 1
    elif pass_rate >= 80 and pass_rate<90:
        return 2
    elif pass_rate >= 70  and pass_rate<80:
        return 3
    elif pass_rate >= 50  and pass_rate<70:
        return 4
    elif pass_rate <50:
        return 5
    else:
        return 0