# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Pydantic models for actions, results, platforms, and workflows."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---

class ExecutionStrategy(str, Enum):
    """How to execute an action."""
    API = "api"
    UI = "ui"
    HYBRID = "hybrid"


class GenerationMode(str, Enum):
    """Script generation mode."""
    PROMPT = "prompt"
    SCREENSHOT = "screenshot"
    RECORDING = "recording"


class ActionType(str, Enum):
    """Types of automation actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    ASSERT = "assert"
    API_CALL = "api_call"
    LOGIN = "login"
    UPLOAD = "upload"


class SelectorStrategy(str, Enum):
    """Selector generation priority order."""
    ARIA_LABEL = "aria-label"
    VISIBLE_TEXT = "visible-text"
    ROLE = "role"
    DATA_TESTID = "data-testid"
    CSS_CLASS = "css-class"
    XPATH = "xpath"


class ActionStatus(str, Enum):
    """Status of an executed action."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    HEALED = "healed"
    SKIPPED = "skipped"


# --- Action Models ---

class Selector(BaseModel):
    """A page element selector with fallbacks."""
    primary: str = Field(description="Primary selector string")
    strategy: SelectorStrategy = Field(default=SelectorStrategy.ARIA_LABEL)
    fallbacks: list[str] = Field(default_factory=list, description="Fallback selectors")
    description: str = Field(default="", description="Human-readable element description")


class ActionStep(BaseModel):
    """A single automation action step."""
    action: ActionType
    selector: Selector | None = Field(default=None, description="Element selector for UI actions")
    value: str | None = Field(default=None, description="Value for type/select actions")
    url: str | None = Field(default=None, description="URL for navigate actions")
    wait_ms: int = Field(default=0, description="Wait time after action")
    description: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionSequence(BaseModel):
    """An ordered sequence of action steps."""
    name: str
    description: str = ""
    platform: str = Field(description="Target platform name")
    steps: list[ActionStep] = Field(default_factory=list)
    strategy: ExecutionStrategy = Field(default=ExecutionStrategy.UI)
    generation_mode: GenerationMode = Field(default=GenerationMode.PROMPT)


# --- Result Models ---

class StepResult(BaseModel):
    """Result of executing a single step."""
    step_index: int
    action: ActionType
    status: ActionStatus
    duration_ms: float = 0.0
    error: str | None = None
    screenshot_path: str | None = None
    healed_selector: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of executing an action sequence."""
    sequence_name: str
    strategy_used: ExecutionStrategy
    total_steps: int
    successful_steps: int = 0
    failed_steps: int = 0
    healed_steps: int = 0
    total_duration_ms: float = 0.0
    step_results: list[StepResult] = Field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """Whether all steps succeeded (including healed ones)."""
        return self.failed_steps == 0

    @property
    def success_rate(self) -> float:
        """Percentage of successful steps."""
        if self.total_steps == 0:
            return 0.0
        return (self.successful_steps + self.healed_steps) / self.total_steps * 100


# --- Platform Models ---

class RateLimit(BaseModel):
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    burst_limit: int = 10
    cooldown_seconds: int = 60


class AuthConfig(BaseModel):
    """Authentication configuration."""
    method: str = Field(description="Auth method: token, oauth, cookie, session")
    token_env_var: str | None = None
    login_url: str | None = None
    credentials_env_prefix: str | None = None


class PlatformConfig(BaseModel):
    """Configuration for a target platform."""
    name: str
    display_name: str = ""
    base_url: str
    has_api: bool = False
    api_base_url: str | None = None
    api_version: str | None = None
    preferred_strategy: ExecutionStrategy = ExecutionStrategy.UI
    rate_limit: RateLimit = Field(default_factory=RateLimit)
    auth: AuthConfig | None = None
    selectors_hint: dict[str, str] = Field(
        default_factory=dict,
        description="Known stable selectors for common elements",
    )
    notes: str = ""


# --- Workflow Models ---

class WorkflowStep(BaseModel):
    """A step in a workflow definition."""
    action: str = Field(description="Action name (e.g., 'post_content', 'create_issue')")
    platform: str
    params: dict[str, Any] = Field(default_factory=dict)
    on_failure: str = Field(default="stop", description="stop | skip | retry")
    max_retries: int = 1


class WorkflowDefinition(BaseModel):
    """A complete workflow definition."""
    name: str
    description: str = ""
    steps: list[WorkflowStep] = Field(default_factory=list)
    schedule: str | None = Field(default=None, description="Cron expression")
    variables: dict[str, str] = Field(default_factory=dict)


# --- Screenshot Analysis Models ---

class ElementInfo(BaseModel):
    """Information about a detected page element."""
    element_type: str = Field(description="button, input, link, text, image, etc.")
    text: str = ""
    location: dict[str, int] = Field(
        default_factory=dict,
        description="Bounding box: x, y, width, height",
    )
    suggested_selector: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ScreenshotAnalysis(BaseModel):
    """Result of analyzing a screenshot."""
    elements: list[ElementInfo] = Field(default_factory=list)
    page_title: str = ""
    page_description: str = ""
    suggested_actions: list[str] = Field(default_factory=list)
