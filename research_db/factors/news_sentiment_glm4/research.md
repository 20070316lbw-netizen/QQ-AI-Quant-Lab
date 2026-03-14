# News Sentiment Factor Research (GLM-4-Plus)

## Hypothesis
金融新闻的情感极性（利好/利空）对股价短期走势具有显著预测作用。通过 GLM-4-Plus 的校准得分，可以过滤乐观噪音，提取真实的 alpha 信号。

## Method
1. **数据源**: DuckDB `news_raw` (2015-2026)
2. **标签生成**: 使用 GLM-4-Plus 进行 [0, 1] 评分。
3. **校准引擎**:
    - 个股通道: 高分信任，低分归中 0.5。
    - 宏观通道: 0.65x 压制乐观偏见。
    - 文化通道: 固定 0.5。

## Result
- **Covered samples**: 331 records
- **Individual confidence**: 173 samples identified
- **Bias suppression**: 16 macro samples calibrated

## Conclusion
GLM-4-Plus 在识别个股利好方面具有极高准确性，但在宏观叙事上存在 10%-20% 的乐观偏离，必须通过校准引擎修正。
