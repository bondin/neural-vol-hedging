import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

DERIBIT_API = "https://www.deribit.com/api/v2"


def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


log = logging.getLogger("deribit.snapshot")

MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}


def parse_expiry_code(code: str) -> Optional[datetime]:
    # '27OCT25' -> 2025-10-27 08:00:00Z
    m = re.fullmatch(r"(\d{1,2})([A-Z]{3})(\d{2})", code or "")
    if not m:
        return None
    day = int(m.group(1))
    mon = MONTHS.get(m.group(2).upper())
    year = 2000 + int(m.group(3))
    if not mon:
        return None
    return datetime(year, mon, day, 8, 0, 0, tzinfo=timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def align_next_slot(start: datetime, minutes: int) -> datetime:
    base = start.replace(second=0, microsecond=0)
    step = minutes
    k = (base.minute // step + 1) * step
    target = base.replace(minute=0) + timedelta(minutes=k)
    if target <= start:
        target += timedelta(minutes=step)
    return target


def write_parquet(
    df: pd.DataFrame,
    out_path: Path,
    compression: str = "zstd",
    row_group_size: int = 200_000,
    use_dictionary: bool = True,
):
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        out_path,
        compression=compression,
        row_group_size=row_group_size,
        use_dictionary=use_dictionary,
    )


@dataclass
class Config:
    interval_minutes: int
    currencies: List[str]
    kind: str
    expired: bool
    max_instruments: int
    data_root: Path
    raw_dir: Path
    processed_dir: Path
    compression: str
    row_group_size: int
    use_dictionary: bool
    max_concurrency: int
    per_request_delay_ms: int
    request_timeout_s: int
    max_retries: int
    retry_delay_ms: int

    @staticmethod
    def from_yaml(path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f)
        return Config(
            interval_minutes=int(y["schedule"]["interval_minutes"]),
            currencies=list(y["universe"]["currencies"]),
            kind=y["universe"]["kind"],
            expired=bool(y["universe"]["expired"]),
            max_instruments=int(y["filters"]["max_instruments"]),
            data_root=Path(y["io"]["data_root"]),
            raw_dir=Path(y["io"]["raw_dir"]),
            processed_dir=Path(y["io"]["processed_dir"]),
            compression=y["io"]["parquet"]["compression"],
            row_group_size=int(y["io"]["parquet"]["row_group_size"]),
            use_dictionary=bool(y["io"]["parquet"]["use_dictionary"]),
            max_concurrency=int(y["runtime"]["max_concurrency"]),
            per_request_delay_ms=int(y["runtime"]["per_request_delay_ms"]),
            request_timeout_s=int(y["runtime"]["request_timeout_s"]),
            max_retries=int(y["runtime"]["max_retries"]),
            retry_delay_ms=int(y["runtime"]["retry_delay_ms"]),
        )


async def get_json(
    client: httpx.AsyncClient, method: str, params: Dict[str, Any]
) -> Dict[str, Any]:
    r = await client.get(DERIBIT_API + method, params=params)
    r.raise_for_status()
    out = r.json()
    if "result" not in out:
        raise RuntimeError(f"Unexpected response: {out}")
    return out["result"]


async def fetch_instruments(
    client: httpx.AsyncClient,
    currency: str,
    kind: str,
    expired: bool,
) -> List[Dict[str, Any]]:
    params = {"currency": currency, "kind": kind, "expired": str(expired).lower()}
    return cast(
        List[Dict[str, Any]], await get_json(client, "/public/get_instruments", params)
    )


async def fetch_order_book(
    client: httpx.AsyncClient,
    instrument: str,
) -> Dict[str, Any]:
    params = {"instrument_name": instrument}
    return await get_json(client, "/public/ticker", params)


def make_row(
    slot_time: datetime,
    underlying: str,
    instrument: str,
    ob: Dict[str, Any],
) -> Dict[str, Any]:
    best_bid = ob["best_bid_price"]
    best_ask = ob["best_ask_price"]
    mid = (
        (best_bid + best_ask) / 2.0
        if (best_bid is not None and best_ask is not None)
        else None
    )
    iv = ob.get("mark_iv")

    parts = instrument.split("-")
    strike = None
    opt_type = None
    expiry_dt = None
    if len(parts) >= 4:
        expiry_dt = parse_expiry_code(parts[1])
        try:
            strike = float(parts[2])
        except Exception:
            strike = None
        opt_type = parts[3]

    greeks = ob.get("greeks")
    if greeks is None:
        delta = gamma = vega = theta = rho = None
    else:
        delta = greeks.get("delta")
        gamma = greeks.get("gamma")
        vega = greeks.get("vega")
        theta = greeks.get("theta")
        rho = greeks.get("rho")

    now = utc_now()
    return {
        "slot_time_utc": slot_time,
        "timestamp_utc": now,
        "underlying": underlying,
        "instrument_name": instrument,
        "expiry_utc": expiry_dt,
        "strike": strike,
        "option_type": opt_type,
        "bid": best_bid,
        "ask": best_ask,
        "mid": mid,
        "iv": iv,
        "delta": delta,
        "gamma": gamma,
        "vega": vega,
        "theta": theta,
        "rho": rho,
        "index_price": ob.get("index_price"),
        "underlying_price": ob.get("underlying_price"),
    }


async def gather_order_books(
    cfg: Config,
    client: httpx.AsyncClient,
    instruments: List[tuple],
) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(cfg.max_concurrency)
    rows: List[Dict[str, Any]] = []
    slot_time = utc_now().replace(second=0, microsecond=0)

    async def worker(under: str, inst: str):
        async with sem:
            retry_count = 0
            while retry_count < cfg.max_retries:
                try:
                    ob = await fetch_order_book(client, inst)
                    rows.append(make_row(slot_time, under, inst, ob))
                    break
                except Exception as e:
                    log.warning("order_book failed for %s: %s", inst, e)
                    retry_count += 1
                    await asyncio.sleep(cfg.retry_delay_ms / 1000.0)

    delay = cfg.per_request_delay_ms / 1000.0
    tasks = []
    for under, inst in instruments:
        tasks.append(asyncio.create_task(worker(under, inst)))
        await asyncio.sleep(delay)
    await asyncio.gather(*tasks)
    return rows


async def snapshot_once(cfg: Config) -> pd.DataFrame:
    timeout = httpx.Timeout(cfg.request_timeout_s, connect=cfg.request_timeout_s)
    async with httpx.AsyncClient(timeout=timeout) as client:
        instruments: List[tuple] = []
        for cur in cfg.currencies:
            try:
                res = await fetch_instruments(client, cur, cfg.kind, cfg.expired)
            except Exception as e:
                log.error("get_instruments failed for %s: %s", cur, e)
                res = []
            for r in res[: cfg.max_instruments]:
                instruments.append((cur, r["instrument_name"]))

        log.info("Total instruments: %d", len(instruments))
        rows = await gather_order_books(cfg, client, instruments)

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["slot_time_utc"] = pd.to_datetime(df["slot_time_utc"], utc=True)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    return df


def build_smiles(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    gb = df.groupby(["underlying", "expiry_utc", "option_type", "strike"], dropna=False)
    agg = gb.agg(
        bid=("bid", "mean"),
        ask=("ask", "mean"),
        mid=("mid", "mean"),
        iv=("iv", "mean"),
        delta=("delta", "mean"),
        gamma=("gamma", "mean"),
        vega=("vega", "mean"),
        theta=("theta", "mean"),
        rho=("rho", "mean"),
        S=("index_price", "mean"),
        F=("underlying_price", "mean"),
    ).reset_index()
    agg.insert(0, "slot_time_utc", df["slot_time_utc"].iloc[0])
    return agg


def write_outputs(cfg: Config, df_raw: pd.DataFrame):
    if df_raw.empty:
        log.warning("Empty snapshot — nothing to write")
        return

    data_root = cfg.data_root
    # Snapshot summary
    slot_time = pd.to_datetime(df_raw["slot_time_utc"].iloc[0], utc=True)
    n_raw = len(df_raw)
    log.info("Snapshot summary | slot=%s | raw_rows=%d", slot_time.isoformat(), n_raw)

    raw_root = data_root / cfg.raw_dir
    proc_root = data_root / cfg.processed_dir

    slot_time = pd.to_datetime(df_raw["slot_time_utc"].iloc[0], utc=True)
    date_str = slot_time.strftime("%Y-%m-%d")
    ts_str = slot_time.strftime("%Y%m%dT%H%M%S")

    for under, dsub in df_raw.groupby("underlying"):
        out_dir = raw_root / f"date={date_str}" / f"underlying={under}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"snapshot_{ts_str}_{under}.parquet"
        write_parquet(
            dsub,
            out_file,
            compression=cfg.compression,
            row_group_size=cfg.row_group_size,
            use_dictionary=cfg.use_dictionary,
        )
        log.info("RAW written: %s rows=%d", out_file, len(dsub))

    smiles = build_smiles(df_raw)
    if smiles.empty:
        log.warning("No smiles produced")
        return
    n_smiles = len(smiles)
    log.info(
        "Smiles summary   | slot=%s | smiles_rows=%d", slot_time.isoformat(), n_smiles
    )

    for under, dsub in smiles.groupby("underlying"):
        out_dir = proc_root / f"date={date_str}" / f"underlying={under}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"smile_{ts_str}_{under}.parquet"
        write_parquet(
            dsub,
            out_file,
            compression=cfg.compression,
            row_group_size=cfg.row_group_size,
            use_dictionary=cfg.use_dictionary,
        )
        log.info("SMILE written: %s rows=%d", out_file, len(dsub))


async def run_loop(cfg: Config):
    while True:
        start = utc_now()
        next_slot = align_next_slot(start, cfg.interval_minutes)
        sleep_s = (next_slot - utc_now()).total_seconds()
        if sleep_s > 0:
            log.info("Sleeping %.1f sec until slot %s", sleep_s, next_slot.isoformat())
            await asyncio.sleep(sleep_s)

        t0 = utc_now()
        log.info("=== Snapshot START slot=%s ===", next_slot.isoformat())
        df = await snapshot_once(cfg)
        if not df.empty:
            df["slot_time_utc"] = pd.to_datetime(next_slot, utc=True)
        write_outputs(cfg, df)
        t1 = utc_now()
        log.info(
            "=== Snapshot END   slot=%s | duration=%.1fs ===",
            next_slot.isoformat(),
            (t1 - t0).total_seconds(),
        )


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/deribit_rest_30m.yaml")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--log-level", default=None)
    args = ap.parse_args()

    setup_logging(level=(args.log_level or "INFO"))
    cfg = Config.from_yaml(args.config)

    if args.once:
        df = asyncio.run(snapshot_once(cfg))
        write_outputs(cfg, df)
    else:
        asyncio.run(run_loop(cfg))


if __name__ == "__main__":
    main()
