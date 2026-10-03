"""Agent mode: activity feed, diff review and approve / reject / undo controls."""
import streamlit as st

from services import api_client

STATUS_TEXT = {
    "planning": "Planning the next step",
    "searching": "Searching the project",
    "reading": "Reading a file",
    "running": "Running code in the sandbox",
    "analyzing": "Analysing",
    "waiting_for_approval": "Waiting for your approval",
    "applying": "Applying the change",
    "verifying": "Verifying the fix",
    "completed": "Completed",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "max_iterations": "Stopped at the iteration limit",
}


def render():
    st.caption("The agent searches, reads, runs and proposes patches. "
               "Nothing is written to disk without your approval.")

    task = st.text_area("Task for the agent", height=80,
                        placeholder="Find the error in payment.py and fix it")
    c1, c2 = st.columns([2, 1])
    if c1.button("Run agent", type="primary", use_container_width=True, disabled=not task):
        _run(task)
    if c2.button("Stop", use_container_width=True, disabled=not st.session_state.agent_session):
        _cancel()

    result = st.session_state.agent_result
    if not result:
        return

    st.markdown("**Agent activity**")
    status = result["status"]
    st.write("Status: %s  -  iteration %d" % (STATUS_TEXT.get(status, status),
                                              result["iteration"]))
    with st.container(height=220):
        for entry in result.get("activity", []):
            mark = "OK  " if entry["ok"] else "FAIL"
            st.text("[%s] #%d %s - %s" % (mark, entry["iteration"], entry["tool"],
                                          entry.get("reason", "")[:70]))
            if entry.get("summary"):
                st.caption(entry["summary"][:300])
        if status == "waiting_for_approval":
            st.text("[WAIT] waiting for approval")

    _render_execution(result.get("execution_output"))
    _render_sources(result.get("sources", []))
    _render_diff(result)

    if result.get("summary"):
        st.info(result["summary"])
    if result.get("error"):
        st.error(result["error"])
    if status in ("completed", "cancelled", "max_iterations"):
        if st.button("Undo last applied change", use_container_width=True):
            _call(api_client.agent_undo)


def _render_execution(execution):
    if not execution:
        return
    with st.expander("Last execution result", expanded=execution["status"] == "error"):
        st.write("status: %s  -  exit code: %s  -  %.3fs"
                 % (execution["status"], execution["exit_code"],
                    execution["execution_time"]))
        if execution["error_category"] != "NONE":
            st.write("%s - %s" % (execution["error_category"],
                                  execution["error_explanation"]))
        if execution["stdout"]:
            st.code(execution["stdout"], language="bash")
        if execution["stderr"]:
            st.code(execution["stderr"], language="bash")


def _render_sources(sources):
    if not sources:
        return
    st.markdown("**Sources**")
    for source in sources:
        st.caption(source)


def _render_diff(result):
    change = result.get("pending_change")
    if not change or change.get("applied"):
        return
    st.markdown("**Proposed change to `%s`**" % change["file_path"])
    if change.get("reason"):
        st.caption(change["reason"])
    st.code(change["diff"] or "(no textual diff)", language="diff")
    c1, c2 = st.columns(2)
    if c1.button("Apply change", type="primary", use_container_width=True):
        _call(api_client.agent_approve, "Applying and verifying...")
    if c2.button("Reject", use_container_width=True):
        _call(api_client.agent_reject)


def _run(task):
    with st.spinner("Agent working..."):
        try:
            result = api_client.agent_run(
                task, st.session_state.project_path, st.session_state.project_id,
                st.session_state.language, st.session_state.current_file,
                st.session_state.code, st.session_state.selected_code)
        except api_client.APIError as exc:
            st.error(str(exc))
            return
    st.session_state.agent_session = result["session_id"]
    st.session_state.agent_result = result
    st.rerun()


def _call(fn, spinner="Working..."):
    session = st.session_state.agent_session
    if not session:
        return
    with st.spinner(spinner):
        try:
            st.session_state.agent_result = fn(session)
        except api_client.APIError as exc:
            st.error(str(exc))
            return
    st.rerun()


def _cancel():
    _call(api_client.agent_cancel, "Stopping...")
