# LTR 调优第三阶段：状态感知加权诊断报告

## 1. 核心结果对标 (Weighted vs. Baseline)
| 指标 | Baseline (Unweighted) | Weighted LTR (Bear=1.5) | Delta |
| :--- | :--- | :--- | :--- |
| **Mean Rank IC** | **0.0214** | **0.0185** | -0.0029 |
| **IC t-stat** | 2.2775 | 1.5574 | -0.7201 |
| **Mean NDCG@10** | 0.4720 | 0.4702 | -0.0018 |
| **IS vs OOS Gap** | 0.0482 | **0.0396** | -0.0086 (改善) |

## 2. 详细分析
1. **稳健性提升，绩效下降**：IS vs OOS 的缺口从 0.048 缩小到 0.039，说明样本加权确实通过抑制牛市噪声起到了正则化作用，使模型更“冷静”。但在 2024 年的测试窗口中，这种冷静牺牲了一部分预测斜率。
2. **显著性丢失**：t-stat 降至 1.55，未能通过显著性检验。这意味着加权后的模型预测力分布更加不均，未能展现出跨年度的长期稳态优势。
3. **Regime 尴尬**：`regime` 特征在 Gain 排名中依然垫底。这进一步印证了全局模型在解析宏观状态标签时的钝化——树模型更倾向于通过个股自身的 Mom/Vol 偏差来分裂节点，而非依赖宏观大盘。

## 3. 同步状态
- **物理路径**：`research_logs_repo/QQ-AI-Quant-Lab/experiments/exp_ltr_regime_weighted/`
- **提交确权**：已物理归档并完成 GitHub 推送。

---
*Research DB - Diagnosis ID: weighted_ltr_v1.0*
