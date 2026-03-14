# 任务：智能金融决策系统 - Phase 3 完成与 Phase 4 衔接

## 路线图与进度跟踪

- [x] **任务 1：DuckDB 中台对接与数据搬迁**
    - [x] 安装环境依赖 (`duckdb`, `pandas`)
    - [x] 配置 `config.py`：设置 `DB_PATH`
    - [x] 运行 `migrate_to_duckdb.py`：显式字段名搬迁 332 条记录
    - [x] 适配 `relabel_v46v.py` 和 `batch_calibrate.py`
    - [x] 修正笔误：`calibrated_score` 范围定义为 `[0, 1]`
- [ ] **任务 2：2015 生存压力测试** [/]
    - [ ] 筛选 2015 年存量新闻样本
    - [/] 运行 DuckDB 版标注流程：识别行业并升级标签 (利好/利空) [进行中]
    - [ ] 校验校准引擎在极端行情下的防御力
- [ ] **任务 3：Phase 4 启动 (SFT 准备)**
    - [ ] 导出 DuckDB 高质量标注集
    - [ ] 定义 Phase 4 微调流水线
- [ ] **任务 4：维护与同步**
    - [ ] 遵循 BAOSTOCK 安全准则
    - [ ] 执行 GitHub 同步

## 知识锚点
- 统一中台：DuckDB (`quant_lab.duckdb`)
- 重构标签：利好/利空/受影响行业
- 版本管理：`model_version` (如 `glm-4-plus_20260314`)
- **要求**：所有报告、注释和文档必须使用中文。
