# Dev_Workspace 极致核心版 (Src Layout)

整个工作区已采用标准的 `src` 布局架构。核心代码通过 `src/` 统一管理，根目录仅保留配置与文档。

---

## 🚀 核心架构图谱

### 📂 [src/](file:///c:/Users/lbw15/Desktop/Dev_Workspace/src)
所有的业务逻辑代码均存放于此。

1. **[trading_agents/](file:///c:/Users/lbw15/Desktop/Dev_Workspace/src/trading_agents)**: (原 TradingAgents) 多智能体交易决策系统。
2. **[kronos/](file:///c:/Users/lbw15/Desktop/Dev_Workspace/src/kronos)**: (原 Kronos) K线大模型预测系统。
3. **[crawlers/](file:///c:/Users/lbw15/Desktop/Dev_Workspace/src/crawlers)**: 金融新闻搜集器及 REST API。

---

## ⚒️ 运行说明

进入 `src` 对应目录后即可按照原方式运行，或在根目录通过指定路径运行。

1. **搜集实时新闻**:
   `python src/crawlers/main.py --topic 股市`

2. **启动行情预测 UI**:
   `python src/kronos/webui/app.py`

3. **运行交易智能体**:
   `python src/trading_agents/main.py`

---
*保持轻量，专注核心。*
