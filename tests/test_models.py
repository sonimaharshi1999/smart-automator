# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Tests for Pydantic models."""

from smart_automator.models import (
    ActionSequence,
    ActionStatus,
    ActionStep,
    ActionType,
    ElementInfo,
    ExecutionResult,
    ExecutionStrategy,
    GenerationMode,
    PlatformConfig,
    RateLimit,
    ScreenshotAnalysis,
    Selector,
    SelectorStrategy,
    StepResult,
    WorkflowDefinition,
    WorkflowStep,
)


class TestSelector:
    """Tests for the Selector model."""

    def test_selector_creation(self) -> None:
        sel = Selector(
            primary='[aria-label="Submit"]',
            strategy=SelectorStrategy.ARIA_LABEL,
            fallbacks=['text=Submit', 'button.submit'],
            description="Submit button",
        )
        assert sel.primary == '[aria-label="Submit"]'
        assert sel.strategy == SelectorStrategy.ARIA_LABEL
        assert len(sel.fallbacks) == 2
        assert sel.description == "Submit button"

    def test_selector_defaults(self) -> None:
        sel = Selector(primary="text=Click me")
        assert sel.strategy == SelectorStrategy.ARIA_LABEL
        assert sel.fallbacks == []
        assert sel.description == ""


class TestActionStep:
    """Tests for the ActionStep model."""

    def test_navigate_step(self) -> None:
        step = ActionStep(
            action=ActionType.NAVIGATE,
            url="https://example.com",
            description="Go to example",
        )
        assert step.action == ActionType.NAVIGATE
        assert step.url == "https://example.com"
        assert step.selector is None

    def test_click_step_with_selector(self) -> None:
        step = ActionStep(
            action=ActionType.CLICK,
            selector=Selector(primary='[aria-label="Submit"]'),
            wait_ms=500,
        )
        assert step.action == ActionType.CLICK
        assert step.selector is not None
        assert step.wait_ms == 500

    def test_type_step(self) -> None:
        step = ActionStep(
            action=ActionType.TYPE,
            selector=Selector(primary='[role="textbox"]'),
            value="Hello World",
        )
        assert step.value == "Hello World"


class TestExecutionResult:
    """Tests for ExecutionResult model."""

    def test_success_rate_all_pass(self) -> None:
        result = ExecutionResult(
            sequence_name="test",
            strategy_used=ExecutionStrategy.UI,
            total_steps=5,
            successful_steps=5,
        )
        assert result.success is True
        assert result.success_rate == 100.0

    def test_success_rate_with_healed(self) -> None:
        result = ExecutionResult(
            sequence_name="test",
            strategy_used=ExecutionStrategy.UI,
            total_steps=4,
            successful_steps=2,
            healed_steps=2,
        )
        assert result.success is True
        assert result.success_rate == 100.0

    def test_success_rate_with_failures(self) -> None:
        result = ExecutionResult(
            sequence_name="test",
            strategy_used=ExecutionStrategy.UI,
            total_steps=5,
            successful_steps=3,
            failed_steps=2,
        )
        assert result.success is False
        assert result.success_rate == 60.0

    def test_success_rate_empty(self) -> None:
        result = ExecutionResult(
            sequence_name="test",
            strategy_used=ExecutionStrategy.UI,
            total_steps=0,
        )
        assert result.success_rate == 0.0


class TestPlatformConfig:
    """Tests for PlatformConfig model."""

    def test_platform_with_api(self) -> None:
        platform = PlatformConfig(
            name="github",
            base_url="https://github.com",
            has_api=True,
            api_base_url="https://api.github.com",
            preferred_strategy=ExecutionStrategy.API,
        )
        assert platform.has_api is True
        assert platform.preferred_strategy == ExecutionStrategy.API

    def test_platform_ui_only(self) -> None:
        platform = PlatformConfig(
            name="linkedin",
            base_url="https://linkedin.com",
            has_api=False,
        )
        assert platform.has_api is False
        assert platform.preferred_strategy == ExecutionStrategy.UI


class TestWorkflowDefinition:
    """Tests for WorkflowDefinition model."""

    def test_workflow_with_schedule(self) -> None:
        wf = WorkflowDefinition(
            name="daily_post",
            description="Post daily",
            steps=[
                WorkflowStep(action="post", platform="linkedin", params={"text": "Hi"}),
            ],
            schedule="0 9 * * 1-5",
        )
        assert wf.name == "daily_post"
        assert len(wf.steps) == 1
        assert wf.schedule == "0 9 * * 1-5"


class TestScreenshotAnalysis:
    """Tests for ScreenshotAnalysis model."""

    def test_analysis_with_elements(self) -> None:
        analysis = ScreenshotAnalysis(
            elements=[
                ElementInfo(
                    element_type="button",
                    text="Submit",
                    confidence=0.9,
                    location={"x": 100, "y": 200, "width": 80, "height": 30},
                ),
            ],
            page_title="Login Page",
        )
        assert len(analysis.elements) == 1
        assert analysis.elements[0].confidence == 0.9
