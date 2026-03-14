# Research Knowledge Base (research_db)

## 结构说明
- `index/`: 索引表 (factors.csv, experiments.csv)，实现跨维索引。
- `factors/`: 因子研究。每个因子拥有独立文件夹，包含元数据、结果 JSON 及研究 Markdown。
- `experiments/`: 训练与回测实验记录。
- `validation/`: 安慰剂测试及异常审计记录。
- `meta/`: 全局研报及排行榜 (leaderboard.json)。

## 研究规范
1. **文件夹即对象**：新增因子或实验时，先建立对应子目录。
2. **数据双轨化**：
    - `results.json`: 机器可读，用于自动化生成排行榜。
    - `research.md`: 人类可读，用于投研决策。
3. **元数据驱动**：`metadata.yaml` 记录作者、日期、状态及公式定义。

---
*Alpha Genome Research Infrastructure*
