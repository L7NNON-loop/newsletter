"""Integração simples com Firebase Realtime Database via REST."""
from __future__ import annotations

import time

import httpx


class FirebasePanel:
    def __init__(self) -> None:
        self.base_url = "https://slayer-bot-pro-v2-default-rtdb.firebaseio.com"
        self._client = httpx.AsyncClient(timeout=8)

    async def set_group_signal_count(self, chat_id: int, count: int) -> None:
        await self._client.put(f"{self.base_url}/panel/groups/{chat_id}/signal_count.json", json=count)

    async def set_group_paused(self, chat_id: int, paused: bool) -> None:
        await self._client.put(f"{self.base_url}/panel/groups/{chat_id}/paused.json", json=paused)

    async def save_signal(self, message: str) -> None:
        payload = {
            "message": message,
            "createdAt": int(time.time() * 1000),
            "status": "active",
            "source": "telegram",
        }
        await self._client.post(f"{self.base_url}/signals.json", json=payload)

    async def close(self) -> None:
        await self._client.aclose()
