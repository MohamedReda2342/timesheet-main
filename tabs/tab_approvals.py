# ./tabs/tab_approvals.py
import streamlit as st
import pandas as pd
from utils import manager_queries as mq
from utils.state_helpers import clear_other_dialogs

@st.dialog("Reject Timesheet")
def reject_timesheet_dialog(entry, approver_id):
    st.warning(f"Rejecting timesheet for {entry['employee_name']}")
    with st.form("rejection_form"):
        comment = st.text_area("Reason (Required)")
        if st.form_submit_button("Confirm Rejection", type="primary"):
            if not comment:
                st.error("Reason required.")
            else:
                mq.update_entry_status(entry['entry_id'], approver_id, 'rejected', comment)
                st.success("Rejected.")
                st.rerun()

def render(user):
    st.subheader("Pending & Submitted Timesheets")
    entries = mq.fetch_submitted_weekly_entries(user['user_id'])
    
    if not entries:
        st.info("No pending timesheets.")
    else:
        df = pd.DataFrame(entries)
        col1, col2 = st.columns(2)
        emp_filter = col1.selectbox("Employee", ["All"] + sorted(df["employee_name"].unique().tolist()))
        status_filter = col2.selectbox("Status", ["All", "draft", "submitted", "approved", "rejected"])
        
        filtered = df.copy()
        if emp_filter != "All": filtered = filtered[filtered["employee_name"] == emp_filter]
        if status_filter != "All": filtered = filtered[filtered["status"] == status_filter]

        if filtered.empty:
            st.warning("No matches.")
        else:
            cols = st.columns([3, 3, 2, 2, 2, 2])
            headers = ["Employee", "Project / Task", "Week", "Hrs", "Approve", "Reject"]
            for c, h in zip(cols, headers): c.write(f"**{h}**")

            for row in filtered.to_dict("records"):
                c = st.columns([3, 3, 2, 2, 2, 2])
                c[0].write(row['employee_name'])
                c[1].write(f"{row['project_name']} / {row['task_name'] or '--'}")
                c[2].write(str(row['week_start_date']))
                c[3].write(f"{row['total_hours']:.2f}")

                if row["status"] == "approved":
                    c[4].success("Approved")
                elif row["status"] == "rejected":
                    c[5].error("Rejected")
                else:
                    if c[4].button("✅", key=f"app_{row['entry_id']}"):
                        mq.update_entry_status(row['entry_id'], user['user_id'], 'approved')
                        st.rerun()
                    if c[5].button("❌", key=f"rej_{row['entry_id']}"):
                        clear_other_dialogs("reject_entry_info")
                        st.session_state.reject_entry_info = row

    # Dialog Invocation
    if st.session_state.get("reject_entry_info"):
        reject_timesheet_dialog(st.session_state.get("reject_entry_info"), user['user_id'])
        del st.session_state["reject_entry_info"]