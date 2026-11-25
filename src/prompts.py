"""Axis 0 - Prompt engineering. The RTCCF framework: Role, Task, Context, Constraints, Format."""
MENTOR = "a pragmatic start-up mentor who works with first-time student founders"


def build(role: str, task: str, context: str = "", constraints: str = "", fmt: str = "") -> str:
    parts = [f"ROLE: You are {role}.", f"TASK: {task}"]
    if context:
        parts.append(f"CONTEXT:\n{context}")
    if constraints:
        parts.append(f"CONSTRAINTS: {constraints}")
    if fmt:
        parts.append(f"OUTPUT FORMAT: {fmt}")
    return "\n\n".join(parts)
