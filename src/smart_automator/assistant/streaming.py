# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""Streaming response parser that extracts POINT tags mid-speech.

Like Clicky, the AI embeds [POINT:x,y:label] commands inline with speech text.
This parser processes the stream chunk-by-chunk, extracting pointer commands
as they arrive and yielding speech segments and pointer events interleaved.
"""

from __future__ import annotations

import re
import subprocess
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generator


class StreamEventType(str, Enum):
    SPEECH = "speech"
    POINT = "point"
    ACTION = "action"
    END = "end"


@dataclass
class StreamEvent:
    """A single event from the streaming parser."""
    event_type: StreamEventType
    text: str = ""
    x: int = 0
    y: int = 0
    label: str = ""
    action_data: dict[str, Any] | None = None


# Matches [POINT:x,y:label] or [POINT:x,y] tags
POINT_PATTERN = re.compile(
    r'\[POINT:(\d+),(\d+)(?::([^\]]*))?\]'
)

# Matches [ACTION:type:params] tags
ACTION_PATTERN = re.compile(
    r'\[ACTION:(\w+)(?::([^\]]*))?\]'
)

STREAMING_SYSTEM_ADDENDUM = """
When pointing at UI elements, embed pointer commands inline with your speech using this format:
[POINT:x,y:label] — where x,y are screen pixel coordinates and label describes the element.

Example response:
"Click the settings button [POINT:1205,45:Settings gear icon] in the top-right corner, then scroll down to [POINT:640,380:Privacy section] the privacy section."

For actions in DO mode, also embed:
[ACTION:click:description] or [ACTION:type:text to type]

Rules:
- Place POINT tags right after mentioning the element
- Use natural speech around the tags
- Multiple POINTs in one response is fine
- Coordinates must be from the screenshot analysis
"""


def parse_response_stream(raw_text: str) -> list[StreamEvent]:
    """Parse a complete response into interleaved speech and pointer events.

    Splits the text at POINT/ACTION tags, yielding speech segments
    and commands in the order they appear.
    """
    events: list[StreamEvent] = []
    pos = 0

    combined = re.compile(
        r'\[POINT:(\d+),(\d+)(?::([^\]]*))?\]|\[ACTION:(\w+)(?::([^\]]*))?\]'
    )

    for match in combined.finditer(raw_text):
        start, end = match.span()

        # Speech text before this tag
        speech = raw_text[pos:start].strip()
        if speech:
            events.append(StreamEvent(event_type=StreamEventType.SPEECH, text=speech))

        if match.group(1) is not None:
            # POINT tag
            events.append(StreamEvent(
                event_type=StreamEventType.POINT,
                x=int(match.group(1)),
                y=int(match.group(2)),
                label=match.group(3) or "",
            ))
        elif match.group(4) is not None:
            # ACTION tag
            events.append(StreamEvent(
                event_type=StreamEventType.ACTION,
                text=match.group(4),
                action_data={"type": match.group(4), "params": match.group(5) or ""},
            ))

        pos = end

    # Remaining speech after last tag
    remaining = raw_text[pos:].strip()
    if remaining:
        events.append(StreamEvent(event_type=StreamEventType.SPEECH, text=remaining))

    events.append(StreamEvent(event_type=StreamEventType.END))
    return events


def stream_and_parse(
    cmd: list[str],
    on_event: Callable[[StreamEvent], None],
    timeout_s: int = 60,
) -> str:
    """Run a subprocess (like claude CLI) and parse output as it streams.

    Reads stdout line-by-line, parsing POINT tags in real-time and
    calling on_event for each speech segment or pointer command.

    Returns the full raw output.
    """
    full_output: list[str] = []
    buffer = ""

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        def read_stream() -> None:
            nonlocal buffer
            for line in iter(proc.stdout.readline, ""):
                full_output.append(line)
                buffer += line

                # Check for POINT tags in the accumulated buffer
                while True:
                    point_match = POINT_PATTERN.search(buffer)
                    if not point_match:
                        break

                    # Emit speech before the tag
                    pre_text = buffer[:point_match.start()].strip()
                    if pre_text:
                        on_event(StreamEvent(
                            event_type=StreamEventType.SPEECH,
                            text=pre_text,
                        ))

                    # Emit the pointer event
                    on_event(StreamEvent(
                        event_type=StreamEventType.POINT,
                        x=int(point_match.group(1)),
                        y=int(point_match.group(2)),
                        label=point_match.group(3) or "",
                    ))

                    buffer = buffer[point_match.end():]

            # Flush remaining buffer
            remaining = buffer.strip()
            if remaining:
                on_event(StreamEvent(event_type=StreamEventType.SPEECH, text=remaining))
            on_event(StreamEvent(event_type=StreamEventType.END))

        reader = threading.Thread(target=read_stream, daemon=True)
        reader.start()
        reader.join(timeout=timeout_s)

        proc.wait(timeout=5)
        return "".join(full_output)

    except Exception as e:
        on_event(StreamEvent(event_type=StreamEventType.SPEECH, text=f"Stream error: {e}"))
        on_event(StreamEvent(event_type=StreamEventType.END))
        return "".join(full_output)


def strip_tags(text: str) -> str:
    """Remove all POINT and ACTION tags from text, returning clean speech."""
    cleaned = POINT_PATTERN.sub("", text)
    cleaned = ACTION_PATTERN.sub("", cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()
