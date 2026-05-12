"""IA adaptativa para otimizar parâmetros da estratégia sem prever resultados."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import pstdev


@dataclass
class StrategyState:
    protection_factor: float = 1.08
    exit_factor: float = 1.32
    entry_sensitivity: float = 0.55
    dynamic_volatility: float = 0.0
    total_signals: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    win_streak: int = 0
    loss_streak: int = 0
    max_drawdown: int = 0
    equity: int = 0
    peak_equity: int = 0
    recent_results: list[bool] = field(default_factory=list)


class AdaptiveStrategyAI:
    def __init__(self, state_path: str | Path) -> None:
        self.state_path = Path(state_path)
        self.state = self._load_state()

    def _load_state(self) -> StrategyState:
        if not self.state_path.exists():
            return StrategyState()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            allowed = StrategyState.__dataclass_fields__.keys()
            return StrategyState(**{k: v for k, v in data.items() if k in allowed})
        except (OSError, json.JSONDecodeError, TypeError):
            return StrategyState()

    def save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(asdict(self.state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update_volatility(self, candles: list[float]) -> float:
        window = candles[-50:] if len(candles) >= 2 else candles
        if len(window) < 2:
            self.state.dynamic_volatility = 0.0
        else:
            mean = sum(window) / len(window)
            self.state.dynamic_volatility = pstdev(window) / max(mean, 0.01)
        self.save()
        return self.state.dynamic_volatility

    def register_result(self, won: bool) -> None:
        self.state.total_signals += 1
        self.state.recent_results.append(won)
        self.state.recent_results = self.state.recent_results[-50:]

        if won:
            self.state.wins += 1
            self.state.win_streak += 1
            self.state.loss_streak = 0
            self.state.equity += 1
        else:
            self.state.losses += 1
            self.state.loss_streak += 1
            self.state.win_streak = 0
            self.state.equity -= 1

        self.state.peak_equity = max(self.state.peak_equity, self.state.equity)
        self.state.max_drawdown = max(
            self.state.max_drawdown,
            self.state.peak_equity - self.state.equity,
        )
        self.state.win_rate = round((self.state.wins / self.state.total_signals) * 100, 2)
        self._rebalance_aggressiveness()
        self.save()

    def _rebalance_aggressiveness(self) -> None:
        recent = self.state.recent_results[-20:]
        if not recent:
            return
        recent_win_rate = sum(recent) / len(recent)
        volatility_penalty = min(self.state.dynamic_volatility, 1.0) * 0.03

        if self.state.loss_streak >= 2 or recent_win_rate < 0.45:
            self.state.exit_factor = max(1.16, self.state.exit_factor - 0.04 - volatility_penalty)
            self.state.protection_factor = max(1.03, self.state.protection_factor - 0.02)
            self.state.entry_sensitivity = min(0.85, self.state.entry_sensitivity + 0.04)
        elif self.state.win_streak >= 3 or recent_win_rate > 0.62:
            self.state.exit_factor = min(1.75, self.state.exit_factor + 0.03)
            self.state.protection_factor = min(1.24, self.state.protection_factor + 0.015)
            self.state.entry_sensitivity = max(0.35, self.state.entry_sensitivity - 0.025)

        self.state.exit_factor = round(self.state.exit_factor, 4)
        self.state.protection_factor = round(self.state.protection_factor, 4)
        self.state.entry_sensitivity = round(self.state.entry_sensitivity, 4)

    def should_enter(self, trend: float, volatility: float) -> bool:
        pressure = trend - (volatility * 0.15)
        return pressure >= -self.state.entry_sensitivity

    def score_label(self) -> str:
        if self.state.total_signals == 0:
            return "CALIBRANDO"
        if self.state.win_rate >= 65 and self.state.win_streak >= 2:
            return "FORTE"
        if self.state.loss_streak >= 2 or self.state.max_drawdown >= 4:
            return "DEFENSIVO"
        return "ESTÁVEL"

    def score_percent(self) -> int:
        base = self.state.win_rate if self.state.total_signals else 50.0
        streak_bonus = min(self.state.win_streak * 3, 12)
        drawdown_penalty = min(self.state.max_drawdown * 4, 25)
        return int(max(0, min(100, math.floor(base + streak_bonus - drawdown_penalty))))
