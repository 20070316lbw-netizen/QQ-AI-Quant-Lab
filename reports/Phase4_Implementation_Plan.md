# 研究数据库 (Research Knowledge Base) 重构计划

为了提升因子研究的可追溯性与 AI 协同效率，我们将研究日志从“平面文件”升级为“对象化目录”结构。

## Proposed Changes

### [Directory Structure]
#### [NEW] `research_db/`

- **index/**: 存储研究对象的扁平化索引 (factors.csv, experiments.csv, strategies.csv)
- **factors/**: 因子深度对象。如 `factors/news_sentiment_v46v/`
- **experiments/**: 实验记录。如 `experiments/exp_2015_crash_retest/`
- **validation/**: 验证性测试 (Placebo tests, Bias audit)
- **strategies/**: 策略设计文档
- **meta/**: 全局元数据与排行榜

---

### [Phase 4 成果沉淀]
#### [NEW] `factors/news_sentiment_glm4/`
- **metadata.yaml**: 定义因子名称、版本、GLM-4 系统提示词哈希、API 参数。
- **research.md**: 记录 Phase 1-4 的演进、校准逻辑 (CalibrationEngine) 的由来。
- **results.json**: 存储本次 331 条样本的标注质量指标 (Coverage, Distribution)。

---

### [自动化同步脚本]
#### [NEW] [update_research_index.py](file:///c:/AI_Workplace/update_research_index.py)
自动扫描各对象目录下的 `results.json` 或 `metadata.yaml`，同步更新 `index/*.csv`。

## Verification Plan
### Automated Tests
1. 运行目录初始化脚本。
2. 运行索引同步脚本，验证 `index/factors.csv` 是否正确捕捉到 `news_sentiment_glm4` 的信息。
