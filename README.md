# QQ-AI-Quant-Lab: Alpha Genome 进化体系 (Evolutionary System) v3.0

[**English**](#english-version) | [**中文版**](#中文版)

---

<a name="english-version"></a>

# English Version

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

## 📊 Key Findings / 核心发现
- **ZZ500 Alpha**: 12-1 Momentum shows a significant t-stat of **2.48** in China's mid-cap space.
- **Top 3 Alpha Genes (Neutralized)**:
  1. `mom_60d_rank` (IC: -0.0439): Robust short-term reversal anchor.
  2. `mom_20d_rank` (IC: -0.0329): Tactical swing driver.
  3. `sp_ratio_rank` (IC: 0.0322): High-stability value guardian (IR > 0.32).
- **A 股低波异常**: 实证确证 A 股存在强烈的“博彩税”特征，低波组合收益显著优于高波组合。

---

<a name="中文版"></a>

# 中文版

## 🚀 项目简介
**Alpha Genome (Alpha 基因组)** 是一个先进的量化投研框架，旨在全球股票市场（目前支持美股与 A 股）中发现稳健的“Alpha 基因”。通过结合 **LambdaRank** 特征排序算法与状态感知的 **市场世界模型 (Market World Model)**，本项目实现了从传统因子回测向环境自适应基因发现的进化。

### 🎯 解决的核心问题
- **因子衰减与环境切换**：自动检测市场状态（牛/熊），并将权重重新分配给最稳健的因子序列 (M/V/L)。
- **信号噪音**：利用正交化与中性化技术剥离市场和行业偏离，暴露纯净的 Alpha 驱动力。
- **低门槛实战**：通过“500元小助手”专门识别低价股（< 5元）中的高 Alpha 机会。

### 💎 核心优势
- **真实市场数据，无合成演示**：基于多年真实的行情与基本面数据构建。
- **样本外验证 (2024-2026)**：在模型从未接触过的数据集上执行严苛测试。
- **发现环境敏感型行为**：例如，在熊市中，波动率残差 (VolRes) 会成为核心 Alpha 驱动力。

## 🧬 Alpha Genome 核心基因序列
- **M (动量)**：短期反转 (M_short) 与 12-1 长期动量 (M_long) 的对冲组合。
- **V (价值)**：经过质量校准的估值指标 (S/P, 1/PS)。
- **L (低波)**：剥离动量干扰后的纯净波动率残差。

## 📊 核心发现
- **中证 500 Alpha**：12-1 动量结构在中盘股表现极其稳健，t-stat 达 **2.48**。
- **A 股低波异常**：实证确证 A 股存在强烈的“博彩税”特征，低波组合收益显著优于高波组合。

---

## 🏗️ Project Structure
- `src/alpharanker/features/`: Evolutionary feature engineering (Neutralization, Scaling).
- `src/alpharanker/models/`: Regime-aware LambdaRank models.
- `research_logs_repo/`: Standardized research audit logs and evaluation reports.
- `src/tui_app.py`: High-performance interactive research terminal (Textual).

## ⚠️ Disclaimer / 免责声明
The code and data in this project are for educational and research purposes only and do not constitute any investment advice. Please use with caution.
本项目的代码和数据仅供学习和研究使用，不构成任何投资建议，请谨慎使用。

---

## 👨‍💻 Team & Contact

**Project Lead:** **Bowei Liu**
- **Email**: [20070316lbw@gmail.com]
- **University**: Hunan University of Information Technology (大一 / Freshman)
- **Major**: Financial Management (财务管理)

**Core Contributors:**
- **Bowei Liu**: Architecture design, manual manual authorship, and result evaluation. (提供了一双手和一个脑子)
- **Gemini**: Coding MASTER, responsible for script writing, model building, and debugging. (代码编写高手)
- **Claude**: Project report auditor and conversational collaborator; raised many critical questions during research. (项目报告检查兼聊天员)
- **ChatGPT**: Project report auditor and advisor; contributed key insights to methodology. (项目报告检查)
- **GLM**: Integrated via API for news labeling; a great teacher for NLP tasks. (API 接入，新闻打标签)

*(Names listed in no particular order; all are core forces of the project.)*
