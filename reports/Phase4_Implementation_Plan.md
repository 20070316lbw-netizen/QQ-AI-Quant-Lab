# 智能金融决策系统：标签体系重构与 2015 压力测试实施计划

本计划旨在完成 Phase 3 的核心交付要求，重点是提升标注精细度并为下一步的 SFT (微调) 准备高质量数据集。

## 用户审核事项
> [!IMPORTANT]
> **DuckDB 中台对接状态**：
> - **已完成**：环境配置 (`config.py`)、数据搬迁 (332 条记录从 SQLite 平移至 `news_labeled`)。
> - **已适配**：标注引擎 (`relabel_v46v.py`) 与批量校准 (`batch_calibrate.py`) 现在直接面向中台工作。
> - **审核点**：我们将以 `glm-4-plus_YYYYMMDD` 作为后续 SFT 训练的主力版本。

## 最新架构变更

### 1. 统一中台层 (Unified Database Center - DuckDB)
- **表名对齐**：使用 `news_labeled` 替代原 `sentiment_analysis`。
- **主键策略**：使用 `UUID` 字符串作为主键，支撑大规模分布式标注。
- **版本管理**：使用 `model_version` (TEXT) 记录完整的审计链路。

### 2. Phase 4：2015 极值回溯执行
#### [NEW] [backtest_2015_runner.py](file:///c:/AI_Workplace/backtest_2015_runner.py)
- 从 DuckDB `news_raw` 筛选 2015 年样本。
- 启动 `relabel_v46v.py` 执行“生存压测”标注。
- 测算 `CalibrationEngine` 在“千股跌停”期间对情绪过热的压制有效性。

### 3. SFT 数据集准备 (Training Prep)
- 导出 `news_labeled` 中 `model_version` 包含最新日期的样本。
- 过滤掉 `reason` 过短或行业为“待定”的低质量数据。

### 3. 校准引擎细节修正 (Calibration Fine-tuning)
#### [FIX] [calibration_engine.py](file:///c:/AI_Workplace/calibration_engine.py)
- **代码匹配优化**：切换至严格正则 `\b(60|68|00|30)\d{4}\b`，滤除日期、金额等数字干扰。
- **个股分流逻辑**：
    - **逻辑选择**：采用“高分才信”模式。
    - **执行规则**：仅信任置信度高的信号（`Score > 0.6` 或 `Score < 0.4`），模糊信号统一归中为 `0.5` 以示谨慎。
- **宏观一致性**：继续维持 **0.65x** 统一压制，解决存量与新增数据的分布对齐问题。

## 验证计划

### 自动化测试
- 运行 `python check_schema.py` 验证数据库字段是否正确。
- 抽样 10 条 2015 年样本进行标注流程测试，验证 `CalibrationEngine` 的压制逻辑是否生效。

### 手动验证
- 检查 `finance_system.db` 中的 `sentiment_analysis` 表，确认 `affected_industry` 字段已填充且标签已对齐。
- 确认标注理由（Reason）是否已使用中文详细描述。
