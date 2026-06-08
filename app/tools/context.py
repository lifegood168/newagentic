from dataclasses import dataclass


@dataclass(frozen=True)
class ToolContext:
    tenant_id: str
    business_line_id: str | None
    user_id: str | None
    run_id: str
    step_id: str
    session_id: str | None
    trace_id: str
    permissions: tuple[str, ...] = ()
