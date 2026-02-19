# Dev_Workspace 工作区架构与功能图谱

本文件旨在介绍当前工作区内各项目的核心功能、模块划分及其相互关系，方便快速定位和开发。

---

## 1. TradingAgents (多智能体交易框架)
**路径**: `/TradingAgents`
基于 LLM 和 LangGraph 的多智能体协作交易研究框架，模拟真实交易团队的决策流程。

### 核心模块说明：
- **`tradingagents/agents/`**: 智能体定义
    - `analysts/`: 分析师团队（基础面、技术面、新闻、情绪分析）。
    - `researchers/`: 研究员团队（多方逻辑与空方逻辑的深度博弈）。
    - `traders/`: 交易员（汇总报告并生成交易提案）。
    - `risk/`: 风控团队（评估波动率、流动性并审核交易）。
- **`tradingagents/graph/`**: 核心决策流
    - `trading_graph.py`: 使用 LangGraph 编排的智能体交互逻辑图。
- **`tradingagents/llm_clients/`**: 模型接入层
    - 支持 OpenAI, Anthropic, Google Gemini, xAI (Grok), Ollama 等多平台。
- **`cli/`**: 交互式命令行工具。
- **`.env.example`**: API 密钥配置模板（已保留）。

---

## 2. Kronos (金融时间序列基础模型)
**路径**: `/Kronos`
首个开源的金融 K 线图大语言模型。

### 核心模块说明：
- **`model/`**: 模型核心（Tokenizer 与 Predictor）。
- **`finetune/`**: 针对 A 股等市场的微调工具集。
- **`webui/`**: 交互式 Web 预测界面。

---

## 3. crawlers (财经新闻数据源)
**路径**: `/crawlers`
实时财经新闻抓取系统。已剔除冗余的单文件脚本，统一使用 `finance_news_collector/` 模块。

---

## 4. examples_archive (示例与演示归档)
**路径**: `/examples_archive`
为了保持项目根目录整洁，所有原本散落在各处的示例、演示及测试脚本已统一移动至此。
- `TradingAgents/`: 包含 Ollama 演示和基础测试脚本。
- `Kronos/`: 包含 K 线预测示例及回归测试脚本。

---

## 5. 共享开发环境
**路径**: `/Dev_Workspace_env`
统一的虚拟环境，支持全工作区项目的运行。

---

## 🛠 快速上手命令
1. **运行智能体交易模拟**:
   `cd TradingAgents && python -m cli.main`
2. **启动行情预测 UI**:
   `cd Kronos/webui && python app.py` (假设入口为 app.py)
3. **抓取最新股市新闻**:
   `cd crawlers && python -m finance_news_collector --topic 股市`

---
*最后更新日期: 2026-02-19*
