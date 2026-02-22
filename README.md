# 🚀 AI 量化与财经智库 (AI-Quant-Lab)

欢迎来到您的 AI 量化实验空间！本项目集成了一套完整的财经情报搜集、行情预测及多智能体交易决策系统。采用了标准的 `src` 布局，保证了代码的整洁与专业性。

---

## 📂 项目结构概览

核心业务逻辑全部存放于 `src/` 目录下：

- **`src/crawlers`**: 财经新闻自动搜集器。支持交互式 CLI 及 REST API。
- **`src/trading_agents`**: 多智能体交易决策系统。通过多个 AI 智能体辩论给出操作建议。
- **`src/kronos`**: K线大模型预测系统。提供直观的 WebUI 展示预测轨迹。

---

## 🛠️ 快速上手

### 1. 环境准备
项目已配置好虚拟环境，请确保使用 `Dev_Workspace_env` 下的 Python。

### 2. 运行财经爬虫 (交互模式)
最简单的使用方式，直接启动菜单选择：
```bash
python src/crawlers/main.py
```
*在菜单中您可以一键搜索主题、自定义关键词，或启动 API 服务器。*

### 3. 运行行情预测 WebUI
可视化查看 K 线预测结果：
```bash
python src/kronos/webui/app.py
```
*启动后访问 [http://localhost:7070](http://localhost:7070)*

### 4. 运行交易智能体决策
获取 AI 团队对特定股票的交易建议：
```bash
python src/trading_agents/main.py
```

---

## 📡 开发者 API (Crawlers)
如果您想通过编程方式获取新闻，可以启动 API 服务：
- **启动**: `python src/crawlers/api.py`
- **获取主题**: `GET http://localhost:5000/api/topics`
- **获取新闻**: `GET http://localhost:5000/api/news?topic=股市`

---

## 🏷️ 版本说明
- **代码架构**: `src` layout (v2.0)
- **核心组件**: FinanceNewsCollector 1.1.0, Kronos-mini, TradingAgents-Graph
- **当前系统**: Antigravity v1.18.4

---
*让数据驱动决策，让 AI 赋能交易。*
