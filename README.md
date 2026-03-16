# QQ-AI-Quant-Lab: Alpha Genome 进化体系 (Evolutionary System) v3.0

[**中文版 (Chinese Version)**](README_zh.md)

---

## 🚀 Project Overview
**Alpha Genome** is an advanced quantitative research framework designed to discover robust "Alpha Genes" across global equity markets (currently supporting US and A-Shares). By combining **LambdaRank** learning-to-rank algorithms with a state-aware **Market World Model**, the project moves beyond simple factor backtesting into environment-adaptive genomic alpha discovery.

### 🎯 Key Problems Solved
- **Factor Decay & Regime Shift**: Automatically detects market regimes (Bull/Bear) and reallocates weights to the most robust factors (M/V/L).
- **Signal Noise**: Utilizes orthogonalization and neutralization to strip away market/sector biases, exposing pure alpha drivers.
- **Low-Cost Accessibility**: Specifically identifies high-alpha opportunities in low-priced stocks (< 5 CNY) via the "500 Yuan Assistant".

### 💎 Core Advantages
- **Real market data, no synthetic demos**: Built on years of actual price and fundamental data.
- **Out-of-sample validation (2024-2026)**: Rigorous testing on data the model has never seen.
- **Discovered regime-dependent factor behavior**: e.g., Volatility Res becomes a primary alpha driver in Bear markets.

## 🧬 Alpha Genome Core Sequences (M+V+L)
- **M (Momentum)**: Short-term reversal (M_short) paired with 12-1 long-term momentum (M_long).
- **V (Value)**: Quality-adjusted valuation metrics (S/P, 1/PS).
- **L (Low Volatility)**: Orthogonalized volatility residuals stripping away momentum bias.

## 📊 Key Findings
- **ZZ500 Alpha**: 12-1 Momentum shows a significant t-stat of **2.48** in China's mid-cap space.
- **Top 3 Alpha Genes (Neutralized)**:
  1. `mom_60d_rank` (IC: -0.0439): Robust short-term reversal anchor.
  2. `mom_20d_rank` (IC: -0.0329): Tactical swing driver.
  3. `sp_ratio_rank` (IC: 0.0322): High-stability value guardian (IR > 0.32).
- **A-Share Low Volatility Anomaly**: Empirical evidence confirms a strong "lottery tax" characteristic in A-shares, where low-volatility portfolios significantly outperform high-volatility ones.

---

## 🏗️ Project Structure
- `src/alpharanker/features/`: Evolutionary feature engineering (Neutralization, Scaling).
- `src/alpharanker/models/`: Regime-aware LambdaRank models.
- `research_logs_repo/`: Standardized research audit logs and evaluation reports.
- `src/tui_app.py`: High-performance interactive research terminal (Textual).

## ⚠️ Disclaimer
The code and data in this project are for educational and research purposes only and do not constitute any investment advice. Please use with caution.

---

## 👨‍💻 Team & Contact

**Project Lead:** **Bowei Liu**
- **Email**: [20070316lbw@gmail.com]
- **University**: Hunan University of Information Technology (大一 / Freshman)
- **Major**: Financial Management (财务管理)

**Core Contributors:**
- **Bowei Liu**: Architecture design, manual manual authorship, and result evaluation.
- **Gemini**: Coding MASTER, responsible for script writing, model building, and debugging.
- **Claude**: Project report auditor and conversational collaborator; raised many critical questions during research.
- **ChatGPT**: Project report auditor and advisor; contributed key insights to methodology.
- **GLM**: Integrated via API for news labeling; a great teacher for NLP tasks.

*(Names listed in no particular order; all are core forces of the project.)*
