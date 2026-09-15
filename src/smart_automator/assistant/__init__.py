# SmartAutomator - Adaptive API/UI Automation Framework
# Author: Maharshi Soni | License: MIT

"""AI Assistant: conversational brain with guide/do/ask modes and streaming pointer parsing."""

from smart_automator.assistant.brain import AssistantBrain, AssistantMode
from smart_automator.assistant.streaming import parse_response_stream, StreamEvent, StreamEventType

__all__ = ["AssistantBrain", "AssistantMode", "parse_response_stream", "StreamEvent", "StreamEventType"]
