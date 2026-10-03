"""Agent planning prompt. The LLM must answer with a single JSON object."""
from backend.agent.tools import TOOL_SPEC

SYSTEM = """You are an AI Agent working inside AI-powered mini IDE.

You work in a loop. On every turn you choose exactly ONE tool to call.
You respond with a SINGLE JSON object and nothing else - no prose, no markdown fences:

{"tool": "<tool name>", "arguments": {...}, "reason": "<one short sentence>"}

Available tools:
""" + TOOL_SPEC + """
Rules:
- Never invent files. Use search_project or read_project_file to find real ones.
- Diagnose before fixing: read the file and run the code to see the real error.
- To change a file you must call write_project_file or generate_fix with the FULL new
  file content. This only proposes a diff; the user must approve it.
- After a change is applied, call run_again to verify, then finish.
- Only claim a fix worked if an execution result actually shows it did.
- Call finish as soon as the task is done or cannot be completed.
"""


def build_user_prompt(state) -> str:
    parts = ["Task from the user:\n" + state.task,
             "Project id: %s" % state.project_id,
             "Project folder open: %s" % ("yes" if state.project_path else "no"),
             "Current file: %s" % (state.current_file or "none"),
             "Language: %s" % (state.language or "python"),
             "Iteration: %d of %d" % (state.iteration, state.max_iterations)]

    if state.current_code.strip():
        parts.append("Current editor code:\n```\n%s\n```" % state.current_code[:4000])
    if state.selected_code:
        parts.append("Selected code:\n```\n%s\n```" % state.selected_code[:2000])

    if state.activity:
        history = []
        for entry in state.activity[-8:]:
            history.append("#%d %s -> %s: %s"
                           % (entry.iteration, entry.tool, "ok" if entry.ok else "FAILED",
                              entry.summary[:600]))
        parts.append("What you have done so far:\n" + "\n".join(history))
    else:
        parts.append("You have not called any tool yet.")

    if state.execution_output:
        e = state.execution_output
        parts.append("Most recent execution: status=%s exit_code=%s category=%s\n"
                     "stdout:\n%s\nstderr:\n%s"
                     % (e.status, e.exit_code, e.error_category,
                        e.stdout[:1500], e.stderr[:1500]))

    pending = state.pending_change()
    if pending:
        parts.append("A change to %s is already waiting for user approval. Call finish."
                     % pending.file_path)

    parts.append("Respond with one JSON object choosing the next tool.")
    return "\n\n".join(parts)


RETRY = ("Your previous reply was not a single valid JSON object with the keys "
         "tool, arguments and reason. Reply again with ONLY that JSON object.")
