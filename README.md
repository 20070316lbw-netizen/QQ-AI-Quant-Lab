# QQ-AI-Quant-Lab (v5.3)

> **AI 驱动的量化财经智库** —— 集成实时新闻、社媒心理、基本面深度分析与 Kronos 时序预测。

![V5.2 Architecture](architecture_v5.png)

## 🚀 架构核心：Algorithmic Decision Chain (V5.2)

QQ-AI-Quant-Lab 现已进化为**硬逻辑算法决策链**模式。我们摒弃了传统的 AI 模糊感性判断，引入了基于数学权重的聚合逻辑，确保每一项投资建议都具备极致的逻辑连贯性与可追溯性。

### 核心机制：量化聚合与风险对冲

系统不再依赖管理层智能体的“主观直觉”，而是通过以下两个核心数学引擎进行决策：

#### 1. 加权因子聚合 (Weighted Factor Aggregator)
在 `Research Manager` 节点中，我们对不同领域的专家报告进行了精准的权重分配：

```python
# 核心权重引擎 (Research Manager)
weights = {
    "bull_researcher": 1.5,
    "bear_researcher": 1.5,
    "market": 1.0,
    "social": 0.8,
    "news": 1.0,
    "fundamentals": 1.2
}

# 计算加权得分
for key, weight in weights.items():
    report = structured_reports.get(key)
    if report:
        point = decision_map.get(report.get("decision"), 0)
        weighted_point = point * report.get("confidence") * weight
        total_score += weighted_point
```

#### 2. 分歧指数与置信度缩放 (Divergence & Scaling)
在 `Risk Judge` 节点中，系统通过计算全队的分歧度来自动修正决策：

```python
# 分歧指数计算 (Risk Judge)
if valid_reports > 0:
    avg_score = sum(scores) / valid_reports
    # 使用方差估算观点分歧度
    variance = sum((s - avg_score) ** 2 for s in scores) / valid_reports
    divergence_index = min(variance, 1.0) # 0.0 (一致) 到 1.0 (严重对立)
    
    # 最终置信度缩放公式
    # 分歧越大、风险越高，置信度下修越狠
    final_confidence = avg_conf * (1 - divergence_index * 0.4) * (1 - avg_risk * 0.3)
```

## 🛠️ 安装与部署 (Requirements)

### 环境要求
- **Python**: `>= 3.11` (推荐使用 3.11+ 以获得最佳 f-string 兼容性)
- **操作系统**: Windows, Linux, macOS (已完成跨平台路径适配)

### 快速安装
```bash
# 克隆仓库
git clone <repository-url>
cd Dev_Workspace

# 安装依赖
pip install -e .
```

### 核心依赖清单 (Dependencies)
项目依赖已在 `pyproject.toml` 中统一管理，主要包括：
- **LangGraph**: 构建多智能体决策图谱。
- **Data Gateway**: `yfinance`, `duckduckgo-search`。
- **Logic Engine**: `numpy`, `stockstats`。
- **ML/AI**: `torch`, `huggingface_hub` (用于 Kronos 推理)。

## 🎮 启动指南

```bash
lab-main
```

1. 在 TUI 菜单中选择 `🤖 智能体研究员`。
2. 输入股票代码（如 `AAPL`, `TSLA`）。
3. 观看 V5.2 决策链如何自动推导出最终的 **量化决策建议**。

---
*Powered by Deepmind Advanced Agentic Coding Team | v5.3-stable*
