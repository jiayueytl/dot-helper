import streamlit as st
import pandas as pd
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

    # Initialize a placeholder for cached data
    if "queried_data" not in st.session_state:
        st.session_state.queried_data = None
        st.session_state.current_run_id = None

    # --- Fetch Data Button ---
    if st.button("Fetch Data") or (
        st.session_state.queried_data is not None 
        and st.session_state.current_run_id == selected_run_id
    ):
        # Fetch new data only if run_id changes
        if (
            st.session_state.current_run_id != selected_run_id
            or st.session_state.queried_data is None
        ):
            with st.spinner(f"Fetching data for run ID: {selected_run_id}..."):
                data = get_pipeline_data(selected_run_id)

            if not data:
                st.warning("No data found for this pipeline run.")
                st.session_state.queried_data = None
                return

            st.session_state.queried_data = pd.DataFrame(data)
            st.session_state.current_run_id = selected_run_id

        # --- Use Cached DataFrame ---
        df = st.session_state.queried_data.copy()

        # --- Tabs for data and visualizations ---
        tab1, tab2 = st.tabs(["🧮 Data View", "📊 Visualizations"])

        with tab1:
            st.subheader("Data Preview and Customization")

            # --- Column Selection ---
            st.markdown("### 🧩 Step 1: Select Columns to Display")
            all_columns = df.columns.tolist()
            selected_columns = st.multiselect(
                "Choose columns to include in the table:",
                options=all_columns,
                default=all_columns,
                key=f"col_select_{selected_run_id}"
            )

            if selected_columns:
                df = df[selected_columns]

                # --- Column Renaming ---
                st.markdown("### ✏️ Step 2: Rename Columns (Optional)")
                rename_mapping = {}
                for col in selected_columns:
                    new_name = st.text_input(
                        f"Rename '{col}' to:",
                        value=col,
                        key=f"rename_{selected_run_id}_{col}"
                    )
                    rename_mapping[col] = new_name

                df = df.rename(columns=rename_mapping)

                # --- Show Data ---
                st.markdown("### 📋 Final Data Table")
                st.dataframe(df)

                # --- Download Option ---
                csv = df.to_csv(index=False, encoding='windows-1252')
                st.download_button(
                    label="⬇️ Download Data as CSV Snapshot (windows-1252)",
                    data=csv,
                    file_name=f"pipeline_data_{selected_run_id}.csv",
                    mime="text/csv",
                    key=f"download_{selected_run_id}"
                )

            else:
                st.warning("Please select at least one column to display.")

        with tab2:
            st.markdown("### 📈 Visualizations")
            create_visualizations(df)
