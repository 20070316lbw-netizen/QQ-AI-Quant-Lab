# Dev_Workspace 极致核心版 (Core Only)

本工作区已完成极致化瘦身，仅保留维持核心功能运行所必需的代码文件。所有文档资源、静态图片、微调逻辑及示例脚本均已剔除。

---

## 🚀 核心架构图谱

### 1. TradingAgents (多智能体交易决策)
**路径**: `/TradingAgents`
- **`tradingagents/`**: 智能体逻辑流。
- **`cli/`**: 交互式入口。
- **`main.py`**: 推理运行脚本。
- **`default_config.py`**: 全局参数配置。

### 2. Kronos (K线大模型预测)
**路径**: `/Kronos`
- **`model/`**: 模型权重加载与预测核心类。
- **`webui/`**: 预测结果可视化界面。

### 3. crawlers (新闻实时搜集)
**路径**: `/crawlers`
- **`finance_news_collector/`**: 模块化爬虫逻辑，适配 DuckDuckGo 搜索。

---

## ⚒️ 运行说明 (极简版)

1. **启动交易评估** (使用内置智能体团队):
   `cd TradingAgents && python main.py`

2. **启动行情预测 Web 界面**:
   `cd Kronos/webui && python app.py`

3. **抓取实时新闻数据**:
   `cd crawlers && python -m finance_news_collector --topic 股市`

---
*保持轻量，专注核心。*
