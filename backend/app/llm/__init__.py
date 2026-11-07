# llm/__init__.py
"""
LLM provider abstraction.

LLM_PROVIDER = none | groq | gemini  (read from environment)

With 'none' the app works fully using rule-based extraction.
All LLM failures fall back to rule-based logic and log the error.
"""
