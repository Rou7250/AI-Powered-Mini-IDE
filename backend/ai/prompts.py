"""All prompt templates in one place."""

BASE_SYSTEM = (
    "You are an AI assistant embedded in AI-powered mini IDE, an intelligent developer environment. "
    "Be precise and concise. When you produce code, always put it in a single fenced code "
    "block so the IDE can extract it. Never invent files, functions or APIs you have not seen."
)

RAG_SYSTEM = (
    "You are an AI programming assistant answering a question about a software project.\n"
    "Use ONLY the retrieved project context when making project-specific claims.\n"
    "If the retrieved context is insufficient, say that the available project context is "
    "insufficient.\n"
    "Do not invent files, functions, classes or relationships.\n"
    "Always mention the relevant filenames in your explanation.\n"
    "When you produce code, put it in a single fenced code block."
)


def general(question):
    return "Question:\n" + question


def current_code(question, language, code, filename=None, selected=""):
    parts = ["Current file: %s" % (filename or "untitled"), "Language: %s" % language]
    if selected.strip():
        parts.append("Selected code:\n```%s\n%s\n```" % (language, selected))
    parts.append("Current code:\n```%s\n%s\n```" % (language, code))
    parts.append("Question:\n" + question)
    return "\n\n".join(parts)


def error_context(question, language, code, execution_output, filename=None):
    return ("Current file: %s\nLanguage: %s\n\n"
            "Current code:\n```%s\n%s\n```\n\n"
            "Execution output / error:\n```\n%s\n```\n\n"
            "Question:\n%s\n\nExplain the root cause and give the corrected code."
            % (filename or "untitled", language, language, code, execution_output, question))


def rag(question, retrieved_context, language="", code="", execution_output="", filename=None):
    parts = []
    if code.strip():
        parts.append("Current file: %s\nCurrent code:\n```%s\n%s\n```"
                     % (filename or "untitled", language, code))
    if execution_output.strip():
        parts.append("Execution output:\n```\n%s\n```" % execution_output)
    parts.append("Retrieved project context:\n" + retrieved_context)
    parts.append("User question:\n%s\n\nProvide a clear explanation and mention the relevant "
                 "filenames." % question)
    return "\n\n".join(parts)


ACTIONS = {
    "explain": ("Explain this code. Cover: purpose, logic step by step, inputs, outputs, "
                "important concepts used, and time/space complexity where relevant."),
    "debug": ("Find the bugs in this code. Use the execution output if provided. Report the "
              "symptom, the most likely root cause and the fix. End with the corrected code "
              "in one fenced block."),
    "fix": ("Fix this code. Report (1) the problem, (2) why it happens, (3) the corrected full "
            "code in one fenced block."),
    "optimize": ("Optimize this code. Report current time/space complexity, the bottleneck, the "
                 "improved approach, then the optimized full code in one fenced block."),
    "refactor": ("Refactor this code for readability, structure, naming and duplication removal, "
                 "keeping behaviour identical. List your changes briefly, then give the full "
                 "refactored code in one fenced block."),
    "tests": ("Generate useful test cases for this code, including edge and failure cases, using "
              "the idiomatic test framework for the language. Give the complete test file in one "
              "fenced block."),
}


def action(kind, language, code, execution_output="", filename=None, instruction=""):
    parts = [ACTIONS[kind]]
    if instruction.strip():
        parts.append("Extra instruction from the user: " + instruction)
    parts.append("File: %s\nLanguage: %s\n```%s\n%s\n```"
                 % (filename or "untitled", language, language, code))
    if execution_output.strip():
        parts.append("Execution output:\n```\n%s\n```" % execution_output)
    return "\n\n".join(parts)
