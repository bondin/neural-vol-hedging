# src/data/cleaning.py
from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from .normalize import standardize


@dataclass
class QCLimits:
    iv_min: float = 0.01
    iv_max: float = 5.0


_ENV_MAP = {
    "spread_rel_max": "QC_SPREAD_REL_MAX",
    "volume_min": "QC_VOLUME_MIN",
    "iv_min": "QC_IV_MIN",
    "iv_max": "QC_IV_MAX",
}


def _load_yaml_dict(path: str) -> Dict[str, Any]:
    """
    Минимальный разбор плоского YAML-подобного файла вида:
    qc:
      a: 1
      b: 2.5
      c: text

    Возвращает словарь верхнего уровня, где секции — это вложенные dict.
    Конвертируем значения: int -> float -> str.
    """
    text: str = Path(path).read_text(encoding="utf-8")

    data: Dict[str, Any] = {}
    current: Optional[Dict[str, Any]] = None  # активная секция (вложенный dict)

    for raw in text.splitlines():
        # исходная строка и её варианты
        line = raw.rstrip("\n")
        stripped = line.strip()

        # пустые строки и комментарии
        if not stripped or stripped.startswith("#"):
            continue

        # ключ верхнего уровня (нет ведущих пробелов)
        if not line.startswith(" "):
            if ":" in line:
                top_key, _ = line.split(":", 1)
                top_key = top_key.strip()
                # открываем/создаём секцию-словарь
                sect: Dict[str, Any] = {}
                data[top_key] = sect
                current = sect
            else:
                # строка верхнего уровня без ":" — игнор
                current = None
            continue

        # пара "k: v" внутри текущей секции
        if current is not None and ":" in stripped:
            k_part, v_part = stripped.split(":", 1)
            k: str = k_part.strip()
            v_str: str = v_part.strip()

            # попытка конвертации значения
            val: Any
            if v_str == "":
                val = ""  # можно заменить на None, если нужно
            else:
                # сначала int, затем float (если есть точка/экспонента, пробуем сразу float)
                try:
                    if "." in v_str or "e" in v_str.lower():
                        val = float(v_str)
                    else:
                        val = int(v_str)
                except ValueError:
                    try:
                        val = float(v_str)
                    except ValueError:
                        val = v_str

            current[k] = val

    return data


def _limits_from_mapping(m: Dict[str, Any]) -> QCLimits:
    base = QCLimits()
    for field in _ENV_MAP.keys():
        if field in m and m[field] is not None:
            try:
                base = replace(base, **{field: float(m[field])})
            except Exception:
                pass
    return base


def _apply_env_overrides(lim: QCLimits) -> QCLimits:
    res = lim
    for field, env_name in _ENV_MAP.items():
        val = os.getenv(env_name)
        if val:
            try:
                res = replace(res, **{field: float(val)})
            except Exception:
                continue
    return res


def get_qc_limits(config_path: Optional[str] = None) -> "QCLimits":
    """
    Определяет источник конфигурации QC:
    1. Явно переданный путь.
    2. Переменная окружения QC_CONFIG.
    3. Локальные файлы qc.yml, qc.yaml.
    Возвращает объект QCLimits.
    """

    # 1️⃣ Правильная инициализация списка-кандидатов
    candidates: list[str] = []

    if config_path:
        candidates.append(config_path)

    env_path = os.getenv("QC_CONFIG")
    if env_path:
        candidates.append(env_path)

    # Добавляем стандартные имена файлов в текущей директории
    candidates.extend(["qc.yml", "qc.yaml"])

    lim = QCLimits()  # предполагается, что класс без аргументов создаёт пустые лимиты

    for p_str in candidates:
        p = Path(p_str)
        if p.exists():
            d: Dict[str, Any] = _load_yaml_dict(p_str)
            lim = _limits_from_mapping(d.get("qc", {}))
            break

    return _apply_env_overrides(lim)


def compute_mid_and_spread(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"bid", "ask"}.issubset(out.columns):
        with np.errstate(divide="ignore", invalid="ignore"):
            out["spread_rel"] = (out["ask"] - out["bid"]) / out["mid"]
    return out


def enforce_bid_ask_rules(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"bid", "ask"}.issubset(out.columns):
        out = out[(out["bid"] >= 0) & (out["ask"] > 0) & (out["ask"] >= out["bid"])]
    return out


def add_moneyness(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if {"strike", "index_price"}.issubset(out.columns):
        with np.errstate(divide="ignore", invalid="ignore"):
            out["moneyness"] = np.log(out["strike"] / out["underlying_price"])
    return out


def flag_iv_outliers(df: pd.DataFrame, limits: QCLimits) -> pd.DataFrame:
    out = df.copy()
    if "iv" in out.columns:
        out["iv_flag_outlier"] = ~out["iv"].between(
            limits.iv_min, limits.iv_max, inclusive="both"
        )
    return out


ONLY_AND_RENAMED = {
    "slot_time_utc": "timestamp",
    "underlying": "underlying",
    "instrument_name": "instrument_name",
    "expiry_utc": "expiry",
    "strike": "strike",
    "option_type": "option_type",
    "bid": "bid",
    "ask": "ask",
    "mid": "mid",
    "iv": "iv",
    "delta": "delta",
    "gamma": "gamma",
    "vega": "vega",
    "theta": "theta",
    "rho": "rho",
    "F": "F",
    "S": "S",
    "spread_rel": "spread",
    "moneyness": "moneyness",
    "iv_flag_outlier": "iv_flag_outlier",
}


def filter_rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(columns=ONLY_AND_RENAMED.values(), index=df.index)
    for k, v in ONLY_AND_RENAMED.items():
        if k not in df.columns:
            raise ValueError(f"Column {k} not found in dataframe")
        out[v] = df[k]
    return out


def clean_snapshot(
    df: pd.DataFrame,
    limits: Optional[QCLimits] = None,
    config_path: Optional[str] = None,
) -> pd.DataFrame:
    if limits is None:
        limits = get_qc_limits(config_path)
    out = standardize(df)
    out = enforce_bid_ask_rules(out)
    out = compute_mid_and_spread(out)
    out = add_moneyness(out)
    out = flag_iv_outliers(out, limits)
    out = filter_rename_columns(out)
    return out.reset_index(drop=True)
