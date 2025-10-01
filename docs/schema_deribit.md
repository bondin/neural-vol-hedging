# Project X — Deribit Data Schema

This document defines the schema (data structure) for raw and processed option chain data from Deribit, used in Project X.  
The schema specifies fields, data types, descriptions, and interpretation rules.  
All timestamps are standardized to UTC.

| Field           | Data Type       | Description |
|-----------------|-----------------|-------------|
| `slot_time_utc` | datetime[UTC]   | Snapshot slot time (aligned to 30 minutes). |
| `timestamp_utc` | datetime[UTC]   | Actual timestamp when the record was captured. |
| `underlying`    | string          | Underlying asset (BTC or ETH). |
| `instrument_name` | string        | Instrument code, e.g. `BTC-27OCT25-40000-C`. |
| `expiry_utc`    | datetime[UTC]   | Option expiry date/time (normalized to 08:00 UTC). |
| `strike`        | float           | Option strike price. |
| `option_type`   | string          | Option type: 'C' (Call) or 'P' (Put). |
| `bid`           | float           | Best bid price. |
| `ask`           | float           | Best ask price. |
| `mid`           | float           | Mid price = (bid+ask)/2. |
| `iv`            | float           | Implied Volatility. |
| `delta`         | float           | Greek: sensitivity of option price to underlying price. |
| `gamma`         | float           | Greek: sensitivity of delta to underlying price. |
| `vega`          | float           | Greek: sensitivity of option price to volatility. |
| `theta`         | float           | Greek: sensitivity of option price to time (time decay). |
| `rho`           | float           | Greek: sensitivity of option price to interest rate. |

### Notes
- All timestamps are in UTC.  
- Missing values (e.g., bid/ask) may be stored as NaN.  
- QC thresholds: IV ∈ (0, 5), Delta ∈ [−1, 1], ask ≥ bid ≥ 0, expiry ≥ slot_time.  
- Data is stored in Parquet format with ZSTD compression and row groups of ~200k.  
