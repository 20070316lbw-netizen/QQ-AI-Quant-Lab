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

### 1. 环境准备与挂载
项目已支持标准安装。请在当前虚拟环境下运行以下命令，即可在任意路径直接调用工具：
```bash
pip install -e .
```

### 2. 核心总入口 (推荐)
直接启动智库控制台，一键进入任一模块：
```bash
lab-main
```

### 3. 各模块快捷命令
安装后，您可以直接在终端输入以下快捷命令启动对应功能：
- **`news-lab`**: 启动财经新闻搜集交互界面。
- **`predict-lab`**: 启动 Kronos K线预测 WebUI。
- **`trade-lab`**: 运行智能体交易决策演示。
- **`api-lab`**: 启动搜集器 REST API 服务器。

---

## 📡 开发者 API (Crawlers)
如果您想通过编程方式获取新闻，可以启动 API 服务：
- **启动**: `python src/crawlers/api.py`
- **获取主题**: `GET http://localhost:5000/api/topics`
- **获取新闻**: `GET http://localhost:5000/api/news?topic=股市`

---

## 🏷️ 版本说明
- **代码架构**: `src` layout (v0.2.0-beta)
- **核心组件**: FinanceNewsCollector 1.1.0, Kronos-mini, TradingAgents-Graph
