# Neural Volatility Surfaces and Deep Hedging

This repository contains a **pilot project** focused on building neural network volatility surfaces and reinforcement learning agents for option hedging.  

The project is designed as a **practical playground** for exploring modern approaches in quantitative finance and financial engineering.  

## Purpose

- To gain **hands-on experience** with option pricing models, volatility surface calibration, and dynamic hedging strategies.  
- To practice working with large datasets, Monte Carlo simulations, and machine learning methods.  
- To prepare myself for further studies and the final project during the **CQF program** (planned for spring).  

## Scope of the Pilot Project

- **Baseline models**: SABR, SVI calibration, no-arbitrage checks.  
- **Neural volatility surfaces**: training surrogates for fast calibration and Greeks inference.  
- **Deep Hedging**: reinforcement learning (PPO) agents for dynamic hedging under realistic frictions.  
- **Monte Carlo simulations**: classical and rough volatility models, surrogate acceleration.  
- **Backtesting**: EOD SPX dataset and crypto intraday dataset.

## Notes

- This is a **pilot project**. Results, code, and methodology are for **educational and training purposes only**.  
- The final CQF project will be on another topic, but the experience from this repository will form the foundation.  

---

*Author: Vasilii Bondin*  

## Project Structure

```
/src/           # source code
  data/         # ingestion and preprocessing scripts
  models/       # neural networks and baseline models
  calib/        # SABR/SVI calibration routines
  hedge/        # reinforcement learning environment and agents
/notebooks/     # Jupyter notebooks for research and experiments
/tests/         # unit tests
/reports/       # generated reports (PDF, DOCX, Markdown)
/data/          # raw and processed datasets (excluded from git)
```

See the full [TODO list](TODO.md) for weekly tasks.

---

## 🚀 Installation & Usage

### 1. Build images
```bash
docker compose build        # build CPU service
docker compose build gpu    # build GPU service
```

### 2. Run container
```bash
docker compose run cpu bash     # CPU container
docker compose run gpu bash     # GPU container (requires NVIDIA Container Toolkit)
```

### 3. Run Jupyter Lab
```bash
make jupyter        # start Jupyter Lab on CPU (http://localhost:8888)
make jupyter-gpu    # start Jupyter Lab on GPU
```

### 4. Run tests & lint
```bash
make test
make lint
make format
make pre-commit
```

### 5. Clean up
```bash
make clean
```

---

📌 With `docker compose` and `Makefile`, all data is mounted from the local `./data` folder into the container at `/app/data`.  
This ensures that large datasets are not baked into the image.
