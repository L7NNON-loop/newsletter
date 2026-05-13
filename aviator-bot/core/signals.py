"""Motor matemático para geração e validação de sinais."""
from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean, pstdev

from core.strategy_ai import AdaptiveStrategyAI


@dataclass(slots=True)
class Signal:
    after: float
    protection: float
    exit: float
    players: str
    average: float
    volatility: float
    trend: float
    ai_score: str
    ai_percent: int


class SignalEngine:
    def __init__(
        self,
        ai: AdaptiveStrategyAI,
        min_candles: int = 20,
        players_min: int = 20,
        players_max: int = 100,
    ) -> None:
        self.ai = ai
        self.min_candles = max(20, min_candles)
        self.players_min = players_min
        self.players_max = players_max

    def build_signal(self, candles: list[float]) -> Signal | None:
        if len(candles) < self.min_candles:
            return None

        window = candles[-self.min_candles :]
        avg = mean(window)
        volatility = pstdev(window) / max(avg, 0.01)
        short = mean(window[-5:])
        previous = mean(window[-10:-5]) if len(window) >= 10 else avg
        trend = (short - previous) / max(previous, 0.01)
        self.ai.update_volatility(candles)

        if not self.ai.should_enter(trend, volatility):
            return None

        after = candles[-1]
        volatility_boost = min(max(volatility, 0.0), 1.25)
        conservative_factor = self.ai.state.protection_factor + (volatility_boost * 0.08)
        aggressive_factor = self.ai.state.exit_factor + (volatility_boost * 0.18) + max(trend, 0) * 0.25

        protection = round(max(1.5, min(3.0, (after * 0.42) + (volatility * 0.35))), 2)
        dynamic_exit_cap = 6.0 if trend < 0.12 or volatility > 0.9 else 10.0
        projected_exit = max(protection + 0.2, (protection * 1.35) + max(trend, 0) * 1.8 - (volatility * 0.3))
        exit_value = round(min(dynamic_exit_cap, projected_exit), 2)
        if protection >= exit_value:
            exit_value = round(protection + 0.10, 2)

        players = self._smart_players(volatility=volatility, trend=trend)
        protection, exit_value = self._clamp_targets(protection, exit_value)
        return Signal(
            after=round(after, 2),
            protection=protection,
            exit=exit_value,
            players=players,
            average=round(avg, 3),
            volatility=round(volatility, 3),
            trend=round(trend, 3),
            ai_score=self.ai.score_label(),
            ai_percent=self.ai.score_percent(),
        )

    def build_fallback_signal(self, candles: list[float]) -> Signal | None:
        if not candles:
            return None

        window = candles[-self.min_candles :] if len(candles) >= self.min_candles else candles
        avg = mean(window)
        volatility = pstdev(window) / max(avg, 0.01) if len(window) > 1 else 0.0
        short = mean(window[-5:]) if len(window) >= 5 else avg
        previous = mean(window[-10:-5]) if len(window) >= 10 else avg
        trend = (short - previous) / max(previous, 0.01)

        after = candles[-1]
        protection = round(max(1.5, min(3.0, (after * 0.40) + 0.25)), 2)
        dynamic_exit_cap = 6.0 if trend < 0.12 or volatility > 0.9 else 9.0
        projected_exit = max(protection + 0.2, (protection * 1.32) + max(trend, 0) * 1.5 - (volatility * 0.25))
        exit_value = round(min(dynamic_exit_cap, projected_exit), 2)
        protection, exit_value = self._clamp_targets(protection, exit_value)
        players = self._smart_players(volatility=volatility, trend=trend)
        return Signal(
            after=round(after, 2),
            protection=protection,
            exit=exit_value,
            players=players,
            average=round(avg, 3),
            volatility=round(volatility, 3),
            trend=round(trend, 3),
            ai_score=self.ai.score_label(),
            ai_percent=self.ai.score_percent(),
        )

    def _clamp_targets(self, protection: float, exit_value: float) -> tuple[float, float]:
        protection = round(min(3.0, max(1.5, protection)), 2)
        exit_value = round(min(15.0, max(3.0, exit_value)), 2)
        if exit_value <= protection:
            exit_value = round(min(15.0, protection + 1.0), 2)
        return protection, exit_value

    def _smart_players(self, volatility: float, trend: float) -> str:
        center = (self.players_min + self.players_max) // 2
        spread = max(8, int((self.players_max - self.players_min) * 0.18))
        trend_boost = int(max(trend, 0) * 40)
        volatility_cut = int(min(volatility, 1.0) * 15)
        low = max(self.players_min, center - spread + trend_boost - volatility_cut)
        high = min(self.players_max, center + spread + trend_boost)
        if low >= high:
            low, high = self.players_min, self.players_max
        first = random.randint(low, max(low, high - 10))
        second = random.randint(first + 1, high)
        return f"{first}–{second}"

    @staticmethod
    def is_green(current_value: float, signal: Signal) -> bool:
        return current_value >= signal.exit
