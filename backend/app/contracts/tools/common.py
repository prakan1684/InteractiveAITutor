from typing import Any, Dict, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel, Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[ToolError] = None

