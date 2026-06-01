"""Prompt profile schema for the dynamic prompt registry."""

from typing import TypedDict


class PromptProfile(TypedDict):
    id: str
    title: str
    description: str
    systemPrompt: str
