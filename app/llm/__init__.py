"""LLM layer: the single generator, providers, prompts and JSON parsing."""

from app.llm.generator import GenerationResult, generate

__all__ = ["GenerationResult", "generate"]
