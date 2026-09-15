# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""CLI interface: run, generate, record, schedule, platforms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from smart_automator import __version__
from smart_automator.config import AppConfig, load_config
from smart_automator.strategy.platform_registry import PlatformRegistry

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="smart-automator")
@click.option("--config", "config_path", type=click.Path(exists=False), default=None)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """SmartAutomator - Adaptive API/UI Automation Framework.

    AI-powered automation that auto-selects between API and UI execution.
    No Page Object Model needed - AI generates resilient selectors dynamically.
    """
    ctx.ensure_object(dict)
    cfg_path = Path(config_path) if config_path else None
    ctx.obj["config"] = load_config(cfg_path)


@cli.command()
@click.argument("instruction")
@click.option("--platform", "-p", default="generic", help="Target platform")
@click.option("--mode", "-m", type=click.Choice(["prompt", "screenshot", "recording"]),
              default="prompt", help="Generation mode")
@click.option("--dry-run", is_flag=True, help="Show generated steps without executing")
@click.pass_context
def run(
    ctx: click.Context,
    instruction: str,
    platform: str,
    mode: str,
    dry_run: bool,
) -> None:
    """Run an automation task from a natural language instruction.

    Example: smart-automator run "Post 'Hello World' on LinkedIn" -p linkedin
    """
    config: AppConfig = ctx.obj["config"]

    console.print(Panel(
        f"[bold blue]SmartAutomator[/bold blue] v{__version__}\n"
        f"Mode: [green]{mode}[/green] | Platform: [yellow]{platform}[/yellow]",
        title="Automation",
    ))

    console.print(f"\n[bold]Instruction:[/bold] {instruction}")

    if mode == "prompt":
        _run_prompt_mode(config, instruction, platform, dry_run)
    elif mode == "screenshot":
        console.print("[yellow]Screenshot mode requires an image path as instruction.[/yellow]")
    elif mode == "recording":
        console.print("[yellow]Recording mode requires a script path as instruction.[/yellow]")


def _run_prompt_mode(
    config: AppConfig,
    instruction: str,
    platform: str,
    dry_run: bool,
) -> None:
    """Execute prompt-based generation mode."""
    from smart_automator.llm.claude_cli import ClaudeCLIProvider

    llm = ClaudeCLIProvider()
    if not llm.is_available():
        console.print("[red]Claude CLI not found. Install with:[/red]")
        console.print("  npm install -g @anthropic-ai/claude-code")
        return

    from smart_automator.generators.prompt_generator import PromptGenerator

    generator = PromptGenerator(llm)

    with console.status("Generating automation steps..."):
        try:
            sequence = generator.generate(instruction, platform)
        except Exception as e:
            console.print(f"[red]Generation failed:[/red] {e}")
            return

    # Display generated steps
    table = Table(title="Generated Action Steps")
    table.add_column("#", style="dim")
    table.add_column("Action", style="cyan")
    table.add_column("Selector", style="green")
    table.add_column("Value", style="yellow")

    for i, step in enumerate(sequence.steps, 1):
        sel = step.selector.primary if step.selector else "-"
        val = step.value or step.url or "-"
        table.add_row(str(i), step.action.value, sel[:50], val[:50])

    console.print(table)

    if dry_run:
        console.print("\n[dim]Dry run complete. No actions executed.[/dim]")
        return

    console.print("\n[bold]Executing...[/bold]")
    console.print("[yellow]Note: Execution requires browser. Use --dry-run to preview.[/yellow]")


@cli.command()
@click.argument("script_path", type=click.Path(exists=True))
@click.option("--platform", "-p", default="generic", help="Target platform")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--humanizer/--no-humanizer", default=True, help="Add humanizer delays")
def enhance(
    script_path: str,
    platform: str,
    output: str | None,
    humanizer: bool,
) -> None:
    """Enhance a raw Playwright recording with AI.

    Example: smart-automator enhance recording.py -p linkedin -o enhanced.py
    """
    from smart_automator.generators.recording_enhancer import RecordingEnhancer
    from smart_automator.llm.claude_cli import ClaudeCLIProvider

    script = Path(script_path).read_text(encoding="utf-8")
    console.print(f"[bold]Enhancing recording:[/bold] {script_path}")

    llm = ClaudeCLIProvider()
    if llm.is_available():
        enhancer = RecordingEnhancer(llm)
        with console.status("AI is enhancing the script..."):
            enhanced = enhancer.enhance(script, platform, add_humanizer=humanizer)
    else:
        console.print("[yellow]Claude CLI not found. Using basic enhancement.[/yellow]")
        enhancer = RecordingEnhancer.__new__(RecordingEnhancer)
        enhanced = RecordingEnhancer.enhance_selectors_only(enhancer, script)

    if output:
        Path(output).write_text(enhanced, encoding="utf-8")
        console.print(f"[green]Enhanced script saved to:[/green] {output}")
    else:
        console.print(Panel(enhanced, title="Enhanced Script", border_style="green"))


@cli.command()
@click.pass_context
def platforms(ctx: click.Context) -> None:
    """List all registered platforms and their capabilities."""
    config: AppConfig = ctx.obj["config"]
    registry = PlatformRegistry(config.platforms_dir)

    table = Table(title="Registered Platforms")
    table.add_column("Platform", style="cyan")
    table.add_column("Has API", style="green")
    table.add_column("Strategy", style="yellow")
    table.add_column("Base URL", style="dim")

    for name, platform in registry.get_all().items():
        table.add_row(
            platform.display_name or name,
            "Yes" if platform.has_api else "No",
            platform.preferred_strategy.value,
            platform.base_url[:40],
        )

    console.print(table)

    if not registry.list_platforms():
        console.print(
            "[dim]No platforms found. Add YAML configs to the platforms/ directory.[/dim]"
        )


@cli.command()
@click.pass_context
def schedule(ctx: click.Context) -> None:
    """Show scheduled automation tasks."""
    from smart_automator.scheduler.cron_scheduler import CronScheduler

    scheduler = CronScheduler()
    tasks = scheduler.list_tasks()

    if not tasks:
        console.print("[dim]No scheduled tasks. Use workflow YAML files to define schedules.[/dim]")
        return

    table = Table(title="Scheduled Tasks")
    table.add_column("Name", style="cyan")
    table.add_column("Cron", style="green")
    table.add_column("Enabled", style="yellow")
    table.add_column("Runs", style="dim")

    for task in tasks:
        table.add_row(
            task.name,
            task.cron_expression,
            "Yes" if task.enabled else "No",
            str(task.run_count),
        )
    console.print(table)


@cli.command()
@click.argument("instruction")
@click.option("--mode", "-m", type=click.Choice(["guide", "do", "ask"]),
              default="ask", help="Assistant mode: guide (explain only), do (act), ask (confirm first)")
@click.option("--voice/--no-voice", default=True, help="Enable voice input/output")
@click.option("--overlay/--no-overlay", default=True, help="Enable visual pointer overlay")
@click.option("--tts", type=click.Choice(["pyttsx3", "system", "elevenlabs"]),
              default="pyttsx3", help="Text-to-speech backend")
@click.option("--whisper-model", default="base", help="Whisper model size (tiny/base/small/medium/large)")
@click.pass_context
def assist(
    ctx: click.Context,
    instruction: str,
    mode: str,
    voice: bool,
    overlay: bool,
    tts: str,
    whisper_model: str,
) -> None:
    """Run a single AI-assisted command with screen awareness.

    Example: smart-automator assist "Open Chrome and go to LinkedIn" --mode do
    """
    from smart_automator.assistant.brain import AssistantBrain, AssistantMode
    from smart_automator.llm.claude_cli import ClaudeCLIProvider

    llm = ClaudeCLIProvider()
    if not llm.is_available():
        console.print("[red]Claude CLI not found.[/red]")
        return

    mode_map = {"guide": AssistantMode.GUIDE, "do": AssistantMode.DO, "ask": AssistantMode.ASK}
    brain = AssistantBrain(llm, mode=mode_map[mode])

    console.print(Panel(
        f"[bold blue]SmartAutomator Assistant[/bold blue] v{__version__}\n"
        f"Mode: [green]{mode}[/green] | Voice: {'on' if voice else 'off'} | Overlay: {'on' if overlay else 'off'}",
        title="AI Assistant",
    ))

    # Capture screenshot for context
    screenshot_path = None
    try:
        from smart_automator.vision.screen_capture import ScreenCapture
        capture = ScreenCapture()
        frame = capture.capture_once()
        screenshot_path = str(capture.save_screenshot(frame, "assist_context.png"))
        console.print("[dim]Screen captured for context.[/dim]")
    except Exception:
        console.print("[yellow]Screen capture unavailable, proceeding without visual context.[/yellow]")

    with console.status("AI is analyzing..."):
        response = brain.process(instruction, screenshot_path)

    console.print(f"\n[bold]Assistant ({response.mode_used.value}):[/bold]")
    console.print(response.speech_text)

    if response.pointers:
        console.print("\n[bold cyan]Visual Pointers:[/bold cyan]")
        for ptr in response.pointers:
            console.print(f"  -> ({ptr.get('x')}, {ptr.get('y')}): {ptr.get('label', '')}")

        if overlay:
            try:
                from smart_automator.vision.overlay import VisualOverlay
                ov = VisualOverlay()
                ov.start()
                for ptr in response.pointers:
                    ov.point_at(ptr.get("x", 0), ptr.get("y", 0), ptr.get("label", ""), 3.0)
                import time
                time.sleep(4)
                ov.stop()
            except Exception:
                pass

    if response.actions:
        from rich.table import Table as RichTable
        table = RichTable(title="Planned Actions")
        table.add_column("#", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Target", style="green")
        table.add_column("Description", style="yellow")
        for i, act in enumerate(response.actions, 1):
            target = f"({act.get('x', '-')}, {act.get('y', '-')})" if act.get('x') else act.get('text', '-')
            table.add_row(str(i), act.get("type", ""), target[:40], act.get("description", "")[:40])
        console.print(table)

        if response.needs_confirmation:
            if click.confirm("Execute these actions?"):
                _execute_desktop_actions(response.actions)
            else:
                console.print("[dim]Actions cancelled.[/dim]")
        elif mode == "do":
            _execute_desktop_actions(response.actions)

    if response.follow_up:
        console.print(f"\n[dim]Next: {response.follow_up}[/dim]")

    if voice:
        try:
            from smart_automator.voice.speaker import VoiceSpeaker, TTSBackend
            backend_map = {"pyttsx3": TTSBackend.PYTTSX3, "system": TTSBackend.SYSTEM, "elevenlabs": TTSBackend.ELEVENLABS}
            speaker = VoiceSpeaker(backend=backend_map[tts])
            if speaker.is_available():
                speaker.speak(response.speech_text)
        except Exception:
            pass


@cli.command()
@click.option("--mode", "-m", type=click.Choice(["guide", "do", "ask"]),
              default="ask", help="Assistant mode")
@click.option("--voice/--no-voice", default=True, help="Enable voice I/O")
@click.option("--overlay/--no-overlay", default=True, help="Enable visual overlay")
@click.pass_context
def listen(ctx: click.Context, mode: str, voice: bool, overlay: bool) -> None:
    """Start interactive voice assistant loop (push-to-talk).

    Example: smart-automator listen --mode do
    """
    from smart_automator.assistant.brain import AssistantMode
    from smart_automator.assistant.session import InteractiveSession, SessionConfig, SessionState
    from smart_automator.llm.claude_cli import ClaudeCLIProvider
    from smart_automator.voice.speaker import TTSBackend

    llm = ClaudeCLIProvider()
    if not llm.is_available():
        console.print("[red]Claude CLI not found.[/red]")
        return

    mode_map = {"guide": AssistantMode.GUIDE, "do": AssistantMode.DO, "ask": AssistantMode.ASK}
    config = SessionConfig(
        mode=mode_map[mode],
        overlay_enabled=overlay,
        voice_enabled=voice,
    )

    console.print(Panel(
        f"[bold blue]SmartAutomator Voice Assistant[/bold blue]\n"
        f"Mode: [green]{mode}[/green] | Speak and I'll respond.\n"
        f"Press Ctrl+C to stop.",
        title="Interactive Mode",
    ))

    def on_state(state: SessionState) -> None:
        icons = {
            SessionState.IDLE: "[dim]Idle[/dim]",
            SessionState.LISTENING: "[yellow]Listening...[/yellow]",
            SessionState.THINKING: "[blue]Thinking...[/blue]",
            SessionState.SPEAKING: "[green]Speaking...[/green]",
            SessionState.ACTING: "[red]Acting...[/red]",
            SessionState.CONFIRMING: "[yellow]Awaiting confirmation...[/yellow]",
        }
        console.print(f"  State: {icons.get(state, str(state))}")

    session = InteractiveSession(llm, config)
    session.run_interactive_loop()


def _execute_desktop_actions(actions: list[dict]) -> None:
    """Execute a list of desktop actions."""
    try:
        from smart_automator.desktop.executor import DesktopExecutor, DesktopAction, DesktopActionType

        executor = DesktopExecutor(humanize=True)
        if not executor.is_available():
            console.print("[red]pyautogui not installed. Run: pip install pyautogui[/red]")
            return

        for i, act in enumerate(actions, 1):
            try:
                action_type = DesktopActionType(act.get("type", "wait"))
            except ValueError:
                console.print(f"  [{i}] [yellow]Unknown action: {act.get('type')}[/yellow]")
                continue

            desktop_action = DesktopAction(
                action_type=action_type,
                x=act.get("x"),
                y=act.get("y"),
                text=act.get("text"),
                keys=act.get("keys"),
                app_name=act.get("app_name"),
                description=act.get("description", ""),
            )
            result = executor.execute(desktop_action)
            status = "[green]OK[/green]" if result.success else f"[red]FAIL: {result.error}[/red]"
            console.print(f"  [{i}] {act.get('type', 'wait')}: {status} ({result.duration_ms:.0f}ms)")

            if not result.success:
                break
    except ImportError:
        console.print("[red]Desktop executor unavailable.[/red]")


@cli.command()
def info() -> None:
    """Show framework information and capabilities."""
    console.print(Panel(
        f"[bold blue]SmartAutomator[/bold blue] v{__version__}\n\n"
        "[bold]Three Generation Modes:[/bold]\n"
        "  1. [green]Prompt[/green] - Natural language to automation script\n"
        "  2. [green]Screenshot[/green] - Image analysis to selectors\n"
        "  3. [green]Recording[/green] - Raw recording to hardened script\n\n"
        "[bold]Voice+Vision Assistant:[/bold]\n"
        "  - [cyan]assist[/cyan] - Single command with screen awareness\n"
        "  - [cyan]listen[/cyan] - Interactive voice loop (push-to-talk)\n"
        "  - Three modes: guide (explain), do (act), ask (confirm)\n\n"
        "[bold]Key Features:[/bold]\n"
        "  - AI-powered selector generation (no POM needed)\n"
        "  - Auto API/UI strategy selection\n"
        "  - Self-healing broken selectors\n"
        "  - Human-like interaction patterns\n"
        "  - Desktop control (mouse, keyboard, app launch)\n"
        "  - Visual overlay pointer\n"
        "  - Voice input (Whisper) and output (TTS)\n"
        "  - Continuous screen capture with change detection",
        title="About",
        border_style="blue",
    ))


if __name__ == "__main__":
    cli()
