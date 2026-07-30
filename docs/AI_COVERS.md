# AI Cover Generation & Watermarking Guide

## Overview

The `scripts/generate_ai_covers.py` script automates the generation of media covers for manifestations using local (Ollama) or cloud (OpenAI, Gemini) LLMs and applies corner watermarks to the generated covers to indicate their AI origin.

## Architecture & FRBR Alignment

AI covers are linked to `Manifestation` entities within the FRBR schema. The metadata about the cover generation process is stored in the `Manifestation`'s `meta` JSON column, including:

- `cover_source`: Records which LLM generated the cover.
- `failed_llm_attempts`: Tracks the number of failed generation attempts for circuit breaking.

## CLI Options & Flags

- `--batch-all-unwatermarked`: Process all manifestations that lack watermarked covers.
- `--dry-run`: Preview changes without saving to the database or modifying images.
- `--watermark-only`: Apply corner watermarks to existing covers without invoking the LLM.
- `--force-retry`: Bypass the circuit breaker (process manifestations even if `failed_llm_attempts >= 3`).
- `--prompt-spec PATH`: Provide the path to a custom prompt template file.
- `--limit N`: Limit the number of items processed in a single batch.

## Circuit Breaker

To prevent runaway costs and infinite loops, a circuit breaker mechanism tracks failed generations in `meta["failed_llm_attempts"]`. If an item fails 3 or more times, it is skipped in future automated runs unless explicitly overridden with the `--force-retry` flag.

## Configuration

The following environment variables configure the script:

- `OLLAMA_URL`: URL for local Ollama instances.
- `OPENAI_API_KEY`: API key for OpenAI generation.
- `GEMINI_API_KEY`: API key for Gemini generation.
- `LLM_TITLE_MAX_WORDS`: Maximum words to extract from the title for prompting.

## Makefile Commands

Quick reference for common automation tasks:

- `make generate-covers`: Run AI cover generation batch for unwatermarked items.
- `make generate-covers-dry`: Dry-run AI cover generation batch.
- `make watermark-covers`: Apply watermarks to existing AI covers without regenerating.
