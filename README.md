# QQ-AI-Quant-Lab: Alpha Genome 进化体系 (v3.0)

> 本体系现已演化为基于 **Alpha Genome (M+V+L)** 核心序列的军工级量化研究平台。我们通过跨越美股（2005-2025）与 A 股（2021-2026）的长周期严苛实证，锁定了具备“慢基因”特性的跨市场获利底座。

## 🧬 Alpha Genome 核心基因序列

不同于传统的因子堆砌，本系统提纯了三大具备极强穿透力的原始基因：
1. **Momentum (M)**: 捕捉动量反转溢价（大盘显著反转，中盘噪音调优）。
2. **Value (V)**: 以 `sp_ratio` (营收市值比) 为核心，展现出跨越 120 天持有期的长线增强能力。
3. **Low Volatility Residual (L)**: 剥离动量效应后的纯净波动率残差 (`vol_60d_res`)，是熊市防御与风险定价的核心。
4. **Secret Project (NLP)**: 基于 GLM-4.6V 的中文金融新闻情感分析模块，通过语义向量提取截面情绪 Alpha，作为第四维基因储备。

---

## 🔬 最新实证里程碑 (2026-03)

### 1. A 股长周期多周期实证
我们在 A 股 58 个月度截面（2021-2026）中确证了 Alpha Genome 的统治力：
- **sp_ratio (价值)**: 120天持有期 Rank IC 高达 **+0.103** (ZZ500)，展现出惊人的长线穿透力。
- **vol_60d_res (低波)**: 在中盘股 (ZZ500) 中表现出极佳的风险隔离效果 (t-stat -2.84)。
- **动量分层**: 大盘股 (HS300) 展现出显著的月度反转效应 (t-stat -2.18)。

### 2. 时序衰减分析 (IC Decay)
实证证明 Alpha Genome 属于“慢基因”，信号半衰期显著长于普通技术指标，支持低换手率的大规模资金容量。

---

## 🧠 核心数学引擎 (The Math Logic)

### 1. Regime-Aware 动态权重矩阵
系统不再使用固定参数，而是根据宏观状态（MA250 穿越及流动性分位）自动调节：
- **信用扩张期**: 激活 ROE (Quality) 与成长基因。
- **防御收缩期**: 锁定 `sp_ratio` 与 `vol_res` 防御仓位。

### 2. IC 显著性检验 (Newey-West 修正)
通过 Newey-West HAC 统计修正，在因子评估阶段剥离时序自相关干扰，确保 t-stat 与显著性结论的稳健与纯正。

---

## 🛠️ 快速启动

### 赛博全息交易战情室 (Web UI)
```bash
streamlit run src/webui.py
```

### 自动化因子审计与监控
```bash
python src/alpharanker/eval/eval_realtime_cn.py # 实时 A 股验证
python src/alpharanker/eval/eval_cn_ic_decay.py   # 衰减分析
```

---

## 📁 系统架构图 (V3)
- `src/alpharanker/data/`: 兼容 Baostock/yfinance 的跨市场数据中台。
- `src/alpharanker/features/`: 包含正交化降维逻辑的特征库。
- `src/alpharanker/models/`: 基于 LambdaRank 框架的环境敏感型模型。
- `research_logs_repo/`: 定向同步云端的研究审计日志库 (QQ-AI-Quant-Lab 专属)。

**致主理人：** 
QQ-AI-Quant-Lab 现已从“模型猜测”进化为“基因驱动”。欢迎引领本体系挺进 2015 极值周期的最终炼金术验证！🚀
