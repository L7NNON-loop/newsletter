"""Integração opcional com Gemini via REST leve, sem dependências Rust/cryptography."""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class GeminiQuizAssistant:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self.models = ("gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-2.0-flash")
        self.recent_questions: list[str] = []
        self.fallback_questions = [
            "Os sinais de hoje estão ajudando vocês? 🎯",
            "Querem que eu continue monitorando forte? 🚀",
            "A estratégia está clara para vocês? 🧠",
            "Gostaram da precisão dos últimos sinais? ✅",
            "O grupo está pronto para as próximas entradas? ⚡",
        ]
        self._fallback_index = 0

    async def engagement_question(self) -> str:
        if not self.api_key:
            return self._fallback_question()

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Crie uma pergunta curta em português para engajar um grupo Telegram sobre sinais Aviator. "
                                f"Não repita estas perguntas recentes: {self.recent_questions[-5:]}"
                            )
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
                    if text and text not in self.recent_questions:
                        self._remember(text)
                        return text
                    return self._fallback_question()
                except Exception as exc:  # noqa: BLE001 - Gemini é opcional e não pode derrubar o bot
                    logger.info("Gemini indisponível no modelo %s; usando fallback se necessário: %s", model, exc)
        return self._fallback_question()

    def _remember(self, question: str) -> None:
        self.recent_questions.append(question)
        self.recent_questions = self.recent_questions[-10:]

    def _fallback_question(self) -> str:
        for _ in range(len(self.fallback_questions)):
            question = self.fallback_questions[self._fallback_index % len(self.fallback_questions)]
            self._fallback_index += 1
            if question not in self.recent_questions:
                self._remember(question)
                return question
        question = f"Estão gostando dos sinais? 🎯 #{self._fallback_index}"
        self._fallback_index += 1
        self._remember(question)
        return question
