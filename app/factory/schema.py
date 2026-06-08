from typing import Any

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    name: str = Field(description="模型 ID，由网关解析")
    temperature: float = 0.7
    max_tokens: int = 2048


class BudgetConfig(BaseModel):
    max_steps: int = 30
    max_tokens: int = 100_000


class AgentTemplateYAML(BaseModel):
    schema_version: str = Field(description="YAML schema 版本，必填")
    code: str = Field(description="Agent 唯一编码")
    description: str = ""
    business_line: str | None = None
    system_prompt: str
    tools: list[str] = Field(default_factory=list, description="Tool code 列表")
    model: ModelConfig
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    session_schema: dict[str, Any] | None = None
