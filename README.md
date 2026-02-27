# QQ-AI-Quant-Lab: 混合智能多因子协同量化中枢 (v2.0)

> 本体系为兼具强韧风控与进攻延展性的**军工级混合智能量化研究平台**。历经 13 个迭代周期（Phase），现已演化为一个囊括**深层神经网络引擎 (Kronos) 短距突刺**、**Fama-French 经典多因子大一统雷达 (O-Score) 长距基座**以及**结构化防暴雷/波动率惩罚网**的超维协同体。
> 平台无缝兼容且经过实弹压测支持美股与 A 股标的（如 600519.SS）。

**特别声明**：本文档兼具架构白皮书及前沿量化公式检索功能，为主理人学成归来的战略复盘提供系统级查阅指引。

---

## 🧭 核⼼理论范式：多维干预与分层共振

在 V2 版宏大架构内，本系统抛弃了单薄的大模型“算命”范式或被动因子持仓，形成了精密级联递退的量化管线：
1. **长期雷达 (多因子选股)**：通过提纯基本面的价值、质量等因素，在庞大资产堆中圈定高分“金手指”，并在计算中平滑授予配资特权。
2. **微观打击 (自回归预测池)**：不强求神谕般的“均值”，而是提取基于 Kronos 在未来30天的“变异振幅区间”与时间趋势。
3. **断手自保 (多重断路器)**：一旦发现高隐形杠杆、现金断层或是宏观恐慌溢出（如雷曼时刻、多次熔断），无视前两级的进攻欲望，物理归零清仓。

---

## 🧠 核心数学引擎 (The Math Logic)

本平台最引以为傲的四大数字防线矩阵，代码核心集中于 `src/trading_signal.py` 以及核心算力层：

### 1. 动能基准测算 (Regime Strength / 伪 Z-Score)
对于未来 30 步的多维采样平均，系统利用不确定性分歧比（信噪化）给出入场基准置信度。
$$
\text{Regime Strength} = \frac{\text{Mean Return}}{\max(\text{Std Return (Uncertainty)}, 0.005)}
$$
- **顺势斩击**：$|\text{Regime Strength}| > 0.5$，直接认定处于强势多头或深度做空状态。
- **混沌迷航**：如果不达标，则为无序震荡区间（Ranging Mixed），建议动能仓位直接折半。

### 2. 黑天鹅巨型波动扣减 (Volatility Discount)
本金永不眠。通过计算得到的时序预期标准差若超频，说明不可测知的毁灭即将到来，必须进行指数级折腰惩罚：
$$
\text{Volatility Discount} = \exp{\Big(-10.0 \times \max\big(0, (\text{Uncertainty} - 3\%)\big)\Big)}
$$
*效果实录：在 2008 崩盘前夜，该机制曾成功将建议仓位剥离至 < 1%，完备存还了流动性。*

### 3. Fama-French 统协多因子 O-Score 得分模型
针对基本面各量纲（百亿市值与市盈倍数不相容），采用反向指标截断衰减映射（如极大市盈率将获得0分），组装为统一的 `0-100` 打分蜘蛛网（Radar Chart）。
$$
\text{O-Score} = \sum_{F \in \{Value, Quality, Size, Momentum, Volatility\}} W_F \cdot F(x) 
$$
在最终交易链中，**若 $O < 40$ 分，此票遭到降维（杠杆削半）；若 $O > 75$ 分神票，分配更多敞口权** ($0.5x \sim 1.5x$ 调仓器)。

### 4. 极端一票否决墙 (Fundamental Bust Override)
直抵公司资产负债表与现金流表的核心，无需 NLP 分析师听高管讲故事：
- $ \text{Debt-to-Equity} > 3.0 $（杠杆爆炒成魔）
- $ \text{Current Ratio} < 0.8 $（随时可能断缴的危险流动性）
只要触发此规则并集公式，$ \text{Final Position} \equiv 0 $ 且向中控台疯狂拉响红灯。

---

## 🛠️ 控制台与战地武器库 (Entry Points)

所有代码高度松耦合，主控制流明确。

### 1. 赛博全息交易战情室 (Web UI)
这是您重归实验室最先应该领略的**极客深色控制台**。涵盖多因子雷达网及一票否决截断呈现：
```bash
# 进入环境并挂载控制台：
streamlit run src/webui.py
# 浏览器访问 localhost:8501 步入指挥室
```

### 2. 时空穿梭与大规模跑批 (Backtest Runner)
允许您把环境切换到 `2008-09-01` 或者 `2020-03-01`，用绝对隔离（Offline Sandbox）并模拟最可怕的时局。该引擎可屏蔽未来函数的干扰。
```bash
python src/backtest/backtest_runner.py
# 跑批产物输出至：src/backtest/results/
```

### 3. Alpha 皮尔逊检验分析仪 (Performance Analyzer)
用来硬核评价某项新特征对于夏普或者真实走势具有决定能力。
```bash
python src/backtest/performance_analyzer.py <你的新结果>.jsonl
```

---

## 📁 系统星图架构目录

```text
src/
├── core/                   # 纯底层量化心脏
│   ├── kronos_engine.py    # Kronos 自回归预测清洗池 
│   ├── multi_factor/       # 🚀 Phase 11 多因子提取与雷达投影核心库
│   └── z_decision.py       # 旧版方向决断遗留组件
├── backtest/               # 坚不可摧的绝缘时空回测环境
│   ├── extreme_data/       # 🚀 断网式黑天鹅模拟靶场 (内含雷曼/疫情等历史真迹)
│   ├── backtest_runner.py  # 全局流水生成器
│   └── performance_analyzer.py # 皮尔逊相关性解算器
├── crawlers/               # 无状态的网络数据爬虫与统一路由门面网关 (Gateway)
├── trading_signal.py       # 🚀 双轨制融合战损级信号总 API 暴露层 (拦截/集成枢纽)
├── webui.py                # 🚀 深度重构的赛博全息终端 (St.tabs/Plotly Radar)
└── tradingagents/          # LangGraph 多智能体协同心智层 (已完全辅助化)
```

**致主理人：** 
当您深入夯实金融和 Python 时，此框架已为您铺垫出跨越重洋（A/美股兼容）、无懈防守的多维基础设施。欢迎归来并引领 QQ-AI-Quant-Lab 挺进巅峰！🚀
