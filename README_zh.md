# QQ-AI-Quant-Lab: Alpha 基因组 (Evolutionary System) v3.0

[**English Version**](README.md)

---

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
- **Top 3 Alpha Genes (Neutralized)**:
  1. `mom_60d_rank` (IC: -0.0439): 稳健的短期反转锚点。
  2. `mom_20d_rank` (IC: -0.0329): 战术波段驱动。
  3. `sp_ratio_rank` (IC: 0.0322): 高稳定性价值守卫 (IR > 0.32)。
- **A 股低波异常**：实证确证 A 股存在强烈的“博彩税”特征，低波组合收益显著优于高波组合。

---

## 🏗️ 项目结构
- `src/alpharanker/features/`: Evolutionary feature engineering (Neutralization, Scaling).
- `src/alpharanker/models/`: Regime-aware LambdaRank models.
- `research_logs_repo/`: Standardized research audit logs and evaluation reports.
- `src/tui_app.py`: High-performance interactive research terminal (Textual).

## ⚠️ 免责声明
本项目的代码和数据仅供学习和研究使用，不构成任何投资建议，请谨慎使用。

---

## 👨‍💻 团队与联系方式

**项目负责人:** **Bowei Liu**
- **Email**: [20070316lbw@gmail.com]
- **University**: 湖南信息学院 (大一 / Freshman)
- **Major**: 财务管理 (Financial Management)

**核心贡献者:**
- **Bowei Liu**: 架构设计、编写说明文档和结果评估。(提供了一双手和一个脑子)
- **Gemini**: 代码编写高手，负责编写脚本、构建模型和调试。
- **Claude**: 项目报告审核兼聊天合作者；在研究过程中提出了许多关键问题。
- **ChatGPT**: 项目报告审核和顾问；为方法论提供了关键见解。
- **GLM**: API 接入进行新闻标记；NLP 任务的好老师。

*(排名不分先后；都是项目的核心力量。)*
