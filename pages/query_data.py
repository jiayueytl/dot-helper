import streamlit as st
import pandas as pd
from datetime import datetime
from utils.api import get_pipeline_runs, get_pipeline_data
from utils.visualizations import create_visualizations

def query_data_page():
    st.header("🔍 Query Pipeline Data")

    # --- Fetch available pipeline runs ---
    if not st.session_state.pipeline_runs:
        with st.spinner("Fetching pipeline runs..."):
            get_pipeline_runs()

    if not st.session_state.pipeline_runs:
        st.error("No pipeline runs available.")
        return

    # --- Select which run to query ---
    run_options = {
        run.get("id", str(i)): f"{run.get('run_name', 'Unknown')} ({run.get('id', 'N/A')})"
        for i, run in enumerate(st.session_state.pipeline_runs)
    }

    selected_run_id = st.selectbox(
        "Select Pipeline Run",
        options=list(run_options.keys()),
        format_func=lambda x: run_options[x],
    )

    # Initialize cached placeholders
    if "queried_data" not in st.session_state:
        st.session_state.queried_data = None
        st.session_state.current_run_id = None
    if "processed_df" not in st.session_state:
        st.session_state.processed_df = None

    # --- Fetch Data Button ---
    if st.button("Fetch Data") or (
        st.session_state.queried_data is not None 
        and st.session_state.current_run_id == selected_run_id
    ):
        # Fetch only if new run or no cached data
        if st.session_state.current_run_id != selected_run_id or st.session_state.queried_data is None:
            with st.spinner(f"Fetching data for run ID: {selected_run_id}..."):
                data = get_pipeline_data(selected_run_id)

            if not data:
                st.warning("No data found for this pipeline run.")
                st.session_state.queried_data = None
                st.session_state.current_run_id = None
                return

            st.session_state.queried_data = pd.DataFrame(data)
            st.session_state.current_run_id = selected_run_id
            st.session_state.processed_df = None

        # Use cached data
        df = st.session_state.queried_data.copy()

        # Tabs
        tab1, tab2 = st.tabs(["🧮 Data View", "📊 Visualizations"])

        with tab1:
            st.subheader("Data Preview and Customization")

            # --- Column Selection (with tickboxes instead of multiselect) ---
            st.markdown("### 🧩 Step 1: Select Columns to Display")

            all_columns = df.columns.tolist()
            selected_columns = []
            cols_per_row = 3
            n_rows = (len(all_columns) + cols_per_row - 1) // cols_per_row

            for i in range(n_rows):
                cols_row = all_columns[i * cols_per_row : (i + 1) * cols_per_row]
                col_objs = st.columns(len(cols_row))
                for c_obj, c_name in zip(col_objs, cols_row):
                    with c_obj:
                        checked = st.checkbox(
                            c_name,
                            value=True,
                            key=f"colcheck_{selected_run_id}_{c_name}"
                        )
                        if checked:
                            selected_columns.append(c_name)

            if selected_columns:
                df_display = df[selected_columns].copy()

                # --- Column Renaming (3 columns per row) ---
                st.markdown("### ✏️ Step 2: Rename Columns (Optional)")

                rename_mapping = {}
                cols_per_row = 3
                n_rows = (len(selected_columns) + cols_per_row - 1) // cols_per_row

                for i in range(n_rows):
                    cols_row = selected_columns[i * cols_per_row : (i + 1) * cols_per_row]
                    col_objs = st.columns(len(cols_row))
                    for c_obj, c_name in zip(col_objs, cols_row):
                        with c_obj:
                            new_name = st.text_input(
                                f"Rename '{c_name}'",
                                value=c_name,
                                key=f"rename_{selected_run_id}_{c_name}"
                            )
                            rename_mapping[c_name] = new_name

                df_display = df_display.rename(columns=rename_mapping)

                # --- Show Data ---
                st.markdown("### 📋 Final Data Table")
                st.dataframe(df_display)

                st.session_state.processed_df = df_display
            else:
                st.warning("Please select at least one column to display.")
                st.session_state.processed_df = None

            # --- Download Controls ---
            st.markdown("---")
            col_f, col_e, col_t = st.columns([1, 1, 1])
            with col_f:
                out_format = st.selectbox(
                    "Format",
                    options=["csv", "json"],
                    index=0,
                    key=f"format_{selected_run_id}"
                )
            with col_e:
                enc = st.selectbox(
                    "Encoding",
                    options=["utf-8", "utf-8-sig", "windows-1252", "latin-1"],
                    index=1,
                    key=f"encoding_{selected_run_id}"
                )
            with col_t:
                add_ts = st.checkbox(
                    "Include timestamp in filename",
                    value=True,
                    key=f"ts_{selected_run_id}"
                )

            # --- Download Button ---
            if st.session_state.get("processed_df") is not None:
                df_for_download = st.session_state.processed_df
                now = datetime.now().strftime("%Y%m%d_%H%M%S") if add_ts else ""
                suffix = f"_{now}" if now else ""
                filename = f"pipeline_data_{selected_run_id}{suffix}"

                try:
                    if out_format == "csv":
                        csv_bytes = df_for_download.to_csv(index=False).encode(enc, errors="replace")
                        file_name = f"{filename}.csv"
                        st.download_button(
                            label=f"⬇️ Download CSV ({enc})",
                            data=csv_bytes,
                            file_name=file_name,
                            mime="text/csv",
                            key=f"download_{selected_run_id}_csv"
                        )
                    else:
                        json_str = df_for_download.to_json(orient="records", lines=True, force_ascii=False)
                        json_bytes = json_str.encode(enc, errors="replace")
                        file_name = f"{filename}.jsonl"
                        st.download_button(
                            label="⬇️ Download JSONL",
                            data=json_bytes,
                            file_name=file_name,
                            mime="application/json",
                            key=f"download_{selected_run_id}_json"
                        )
                except Exception as e:
                    st.error(f"Failed to prepare download: {e}")
            else:
                st.info("No processed data available for download yet.")

        with tab2:
            st.markdown("### 📈 Visualizations")
            try:
                vis_df = st.session_state.processed_df if st.session_state.processed_df is not None else df
                create_visualizations(vis_df)
            except Exception as e:
                st.error(f"Error creating visualizations: {e}")
