"""Cliente resiliente para a API de velas do Aviator."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

import httpx

logger = logging.getLogger(__name__)


class AviatorAPIError(RuntimeError):
    """Erro controlado para falhas de API ou payload inválido."""


@dataclass(slots=True)
class CandleSnapshot:
    values: list[float]

    @property
    def latest(self) -> float:
        return self.values[-1]


class AviatorAPIClient:
    def __init__(self, api_url: str, timeout: float = 10.0) -> None:
        self.api_url = api_url
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def fetch_candles(self) -> CandleSnapshot:
        try:
            response = await self._client.get(self.api_url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Falha HTTP ao consultar velas: %s", exc)
            raise AviatorAPIError(str(exc)) from exc
        except ValueError as exc:
            logger.warning("Resposta da API não é JSON válido: %s", exc)
            raise AviatorAPIError("JSON inválido") from exc

        values = self._parse_payload(payload)
        return CandleSnapshot(values=values)

    @staticmethod
    def _parse_payload(payload: dict) -> list[float]:
        if not payload.get("ok"):
            raise AviatorAPIError("API retornou ok=false")

        raw_values = payload.get("valores")
        if not isinstance(raw_values, Iterable):
            raise AviatorAPIError("Campo valores ausente ou inválido")

        values: list[float] = []
        for item in raw_values:
            try:
                values.append(float(item))
            except (TypeError, ValueError):
                logger.debug("Ignorando vela inválida: %r", item)

        if not values:
            raise AviatorAPIError("API retornou lista de velas vazia")
        # A API retorna o valor mais recente primeiro; normalizamos para
        # ordem cronológica (mais antigo -> mais recente).
        values.reverse()
        return values
