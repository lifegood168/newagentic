from typing import Any, Literal

from pydantic import BaseModel


class StepStart(BaseModel):
    type: Literal["step.start"] = "step.start"
    step_id: str
    step_type: str
    seq: int


class ModelDelta(BaseModel):
    type: Literal["model.delta"] = "model.delta"
    step_id: str
    text: str


class ModelToolCall(BaseModel):
    type: Literal["model.tool_call"] = "model.tool_call"
    step_id: str
    tool_name: str
    args: dict[str, Any]


class ToolStart(BaseModel):
    type: Literal["tool.start"] = "tool.start"
    step_id: str
    tool_name: str


class ToolEnd(BaseModel):
    type: Literal["tool.end"] = "tool.end"
    step_id: str
    tool_name: str
    result: Any | None = None
    error: str | None = None


class StepEnd(BaseModel):
    type: Literal["step.end"] = "step.end"
    step_id: str
    status: str


class RunEnd(BaseModel):
    type: Literal["run.end"] = "run.end"
    run_id: str
    status: str
    error: str | None = None
