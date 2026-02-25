# QQ-AI-Quant-Lab: Neuro-Symbolic 混合智能量化终点 (Phase 6 完结版)

> 本仓库是一个**工业级的混合智能量化研究平台**。在历经六个大阶段的重构后，系统从“依赖大模型盲猜涨跌”进化为了**『统计学主导、NLP情绪因子辅助』的双轨制 (Dual-Track) 架构**。这套系统以时间序列预测大模型 (Kronos) 为心脏，辅以严格的防未来函数及严谨的统计检验引擎。

**特别提示**：这份 README 是为主理人（您）在学习回归后无缝接手而撰写的系统全貌“白皮书”。

---

## 🧭 核⼼理论范式：从“预测方向”到“预测分布与波动” 

本系统最核心的颠覆性升级在于：**彻底放弃强迫大模型去预测“一个单一的价格终点”。** 
因为带有温度采样的自回归时序模型 (Autoregressive Inference)，它的每一次推演生成的是一条“可能的未来轨迹”。因此，本项目的系统哲学是：利用大模型的多重采样 (Ensemble)，提取**未来的预测极值（区间）和标准差（不确定性）**。这成为了挖掘真实 Alpha 的圣杯。

---

## 🧠 核心数学引擎 (The Math Logic)

本项目底层决策链已实现全面透明化与公式化。核心逻辑集中在 `src/core/kronos_engine.py` 与 `src/trading_signal.py` 之中：

### 1. 动量状态判定 (Regime Strength / 原 Z-Score)
系统不盲从预测均值，而是结合该次预测的分歧度计算出一种信噪比概念的指数：

$$
\text{Regime Strength} = \frac{\text{Mean Return}_{(30步平均期望收益)}}{\max(\text{Std Return}_{(不确定性标准差)}, 0.005_{噪音拦截地板})}
$$

- **强趋势 (Strong Regime)**：$|\text{Regime Strength}| > 0.5$ 且波动适中。此时动量极强，直接顺势做多/做空。
- **均值回归 (Ranging Regime)**：$|\text{Regime Strength}| \le 0.5$ 或被极高波动打断。此时系统判定为“垃圾时间/无序震荡”，自动放弃趋势追踪或将杠杆减半。

### 2. 黑天鹅与高波动惩罚机制 (Volatility Discount)
量化的第一要务是活下去。如果在采样集成中发现 Kronos 的未来不确定性异常巨大，系统将触发指数级的仓位强平保护：

$$
\text{Volatility Discount} = \exp{\Big(-10.0 \times \max\big(0, (\text{Uncertainty} - 3\%)\big)\Big)}
$$

*解读：当预测标准差超过 3% 后，波动每增加一点，推荐持仓就会断崖式下跌，防止由于宏观消息即将落地导致的双杀爆仓。*

### 3. 双轨融合：量化信号与自然语言情绪结合
在确定了绝对客观的数学仓位后，系统的 NLP 外脑（各类研究员 Agents）会吐出情绪因子，以轻微放大或缩小乘数的形式挂载在最终决策上：

$$
\text{Final Confidence} = \tanh(|\text{Regime Strength}|) \times \text{Volatility Discount} \times (1 + \lambda_{s} \cdot \text{Sentiment}) \times (1 - \text{Risk})
$$

（注：若处在震荡市中，仓位还会在此基础上再被主观砍半）。

---

## 🛠️ 三大实战武器库 (Entry Points)

当前项目的代码已做到完全解耦且开箱即用。主理人回归后，任何策略调优都可以通过以下三个入口闭环完成：

### 1. 可视化交易控制台 (Web UI)
这是查看单只股票最新量化推演和波动作图的最直观武器（依赖于 Streamlit）：
```bash
# 在终端中启动面板，然后在浏览器打开 http://localhost:8501
streamlit run src/webui.py
```

### 2. 严谨冷酷的大规模跑批机 (Backtest Runner)
用于扫盘海量历史数据。该引擎已开启 `as_of_date` 防前视墙，支持全盘并行生成用于统计的只读快照（JSONL 格式）。
```bash
# 股票池和参数请在 src/backtest/config.py 中配置
python src/backtest/backtest_runner.py
# 运行后会在此目录下生成一个巨大的 jsonl 数据集：src/backtest/results/
```

### 3. Alpha 相关性验证器 (Performance Analyzer)
用来检验您的任何改动是否真正有效。它会吞噬刚才的跑批日志，分别校验 1D 和 5D 下的胜率，以及**决定生死的核心指标：Pearson 相关性**。
```bash
# 替换为您刚刚跑出来的最新日志名字即可
python src/backtest/performance_analyzer.py src\backtest\results\backtest_xxx.jsonl
```

---

## 📁 核心代码结构概览

```text
src/
├── core/                   # 纯底层量化心脏
│   ├── kronos_engine.py    # Kronos 预测特征清洗 (提供 Z-score 和预期标准差)
│   └── z_decision.py       # 旧版方向决断遗留组件
├── backtest/               # Phase 6 终极独立回测框架
│   ├── config.py           # 股票池与周期配置中心
│   ├── backtest_runner.py  # 绝对时间轴切面推进历史预演
│   └── performance_analyzer.py # 皮尔逊相关性及胜率解算器
├── trading_signal.py       # 双轨制融合信号总 API 暴露层
├── webui.py                # Streamlit Web 面板启动器
├── crawlers/               # 无状态的网络数据爬虫封装网关 (yfinance 等)
└── tradingagents/          # LangGraph 多智能体协同心智层 (被降权打辅助)
```

## 🗓️ NEXT STEP (写给修学归来的主理人)

当您巩固完了 Pandas 以及统计学原理后，我们的目标将踏入更加迷人的深水区：
1. **套利模式开发**：由于最新测试得出 `Predicted_Range` 与未来实际振幅的相关性高达 `0.38`，这给了我们开发“双向网格交易”或“隐含期权波动率套利”的无限可能。
2. **多因子组合**：尝试引入换手率、市盈率等更多外部因子组合至现在的单维特征矩阵中。

**祝武运昌隆！** 🚀
