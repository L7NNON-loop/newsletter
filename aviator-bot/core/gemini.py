"""Integração opcional com Gemini via REST leve, sem dependências Rust/cryptography."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class GeminiQuizAssistant:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self.models = ("gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash")

    async def engagement_question(self) -> str:
        if not self.api_key:
            return "Estão gostando dos sinais? 🎯"

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": "Crie uma pergunta curta em português para engajar um grupo Telegram sobre sinais Aviator."
                        }
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=12) as client:
            for model in self.models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    response = await client.post(url, params={"key": self.api_key}, json=payload)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0].get("text", "").strip()
                    return text or "Estão gostando dos sinais? 🎯"
                except Exception as exc:  # noqa: BLE001 - Gemini é opcional e não pode derrubar o bot
                    logger.info("Gemini indisponível no modelo %s; usando fallback se necessário: %s", model, exc)
        return "Estão gostando dos sinais? 🎯"
