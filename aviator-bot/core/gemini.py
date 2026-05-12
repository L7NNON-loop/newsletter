"""Integração opcional com Gemini para textos de engajamento."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class GeminiQuizAssistant:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self._model = None
        if api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel("gemini-1.5-flash")
            except Exception as exc:  # noqa: BLE001 - Gemini is optional
                logger.warning("Gemini indisponível; usando fallback local: %s", exc)

    async def engagement_question(self) -> str:
        if not self._model:
            return "Estão gostando dos sinais? 🎯"
        try:
            response = await self._model.generate_content_async(
                "Crie uma pergunta curta em português para engajar um grupo Telegram sobre sinais Aviator."
            )
            return (response.text or "Estão gostando dos sinais? 🎯").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha Gemini; usando pergunta padrão: %s", exc)
            return "Estão gostando dos sinais? 🎯"
