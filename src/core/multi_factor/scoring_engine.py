import math
from typing import Dict, Any

class ScoringEngine:
    """
    多因子模型量纲映射归一化引擎 (0 ~ 100 分制打分)
    该模块负责将不同量纲（如百亿市值和几十倍的市盈率）的数据
    平滑地投射到一张有统一度量衡的“雷达图”或“分数卡”中。
    """
    
    @staticmethod
    def _score_smaller_is_better(value: float, sweet_spot: float, max_punish: float) -> float:
        """
        反向指标得分（数值越小，分数越高）
        例如：PE、市值
        - 如果极其小（甚至低于 sweet_spot），拿满分 100
        - 随着数值指数上升，分数向 0 衰减
        """
        if value is None or math.isnan(value):
            return 50.0 # 找不到数据给一个中庸平庸分
        
        if value <= sweet_spot:
            return 100.0
            
        # 大于甜蜜点后，基于拉普拉斯/指数衰减
        decay_rate = 1.5 / (max_punish - sweet_spot) # 衰减系数
        distance = value - sweet_spot
        score = 100.0 * math.exp(-decay_rate * distance)
        return max(0.0, min(100.0, score))
        
    @staticmethod
    def _score_larger_is_better(value: float, sweet_spot: float, min_punish: float) -> float:
        """
        正向指标得分（数值越大，分数越高）
        例如：ROE，净利润率，现流
        """
        if value is None or math.isnan(value):
            return 50.0
            
        if value >= sweet_spot:
            return 100.0
            
        if value <= min_punish:
            return 0.0
            
        # 在区间内进行线性或微曲率插值
        ratio = (value - min_punish) / (sweet_spot - min_punish)
        return max(0.0, min(100.0, ratio * 100.0))
        
    @staticmethod
    def score_value(pe: float, pb: float) -> float:
        """
        价值因子打分：重仓去挑低市盈率 (PE) 与低市净率 (PB) 的金手指
        在美股，PE 15 以下算便宜 (80~100)，30 算高估，60 以上就是讲故事(不及格)
        """
        pe_s = ScoringEngine._score_smaller_is_better(pe if pe and pe > 0 else 100, sweet_spot=12, max_punish=45)
        # 对于亏损票 (PE < 0)，给出最低价值分，因为它是黑洞
        if pe is not None and pe <= 0:
            pe_s = 0.0
            
        pb_s = ScoringEngine._score_smaller_is_better(pb if pb and pb > 0 else 10, sweet_spot=1.5, max_punish=5.0)
        
        return 0.7 * pe_s + 0.3 * pb_s
        
    @staticmethod
    def score_quality(cr: float, de: float, pm: float, roe: float) -> float:
        """
        质量因子打分：有钱、没债、下金蛋的母鸡
        """
        # Current Ratio: 流动性健康，大于 1.5 是安全屋
        cr_s = ScoringEngine._score_larger_is_better(cr, sweet_spot=1.8, min_punish=0.5)
        
        # Debt to Equity: 低负债，超过 2 倍就要惩罚
        de_s = ScoringEngine._score_smaller_is_better(de if de and de >= 0 else 0, sweet_spot=0.5, max_punish=3.0)
        
        # Profit Margin: 利润率 20%+ 就是印钞机，<0 直接暴死
        pm_s = ScoringEngine._score_larger_is_better(pm, sweet_spot=0.20, min_punish=0.0)
        
        # ROE: 股东回报，15%+ 为极佳，<0 减分
        roe_s = ScoringEngine._score_larger_is_better(roe, sweet_spot=0.15, min_punish=0.0)
        
        return 0.2 * cr_s + 0.3 * de_s + 0.25 * pm_s + 0.25 * roe_s

    @staticmethod
    def score_size(market_cap: float) -> float:
        """
        规模因子 (小盘) 打分：市值越小越容易被“炒上天”。
        2e9 (20亿) 甜蜜点，上方开始指数惩罚，到 2e11 (2000亿) 就完全吃不到小盘溢价了。
        """
        if market_cap is None:
            return 50.0
        
        # 为了防溢出，直接转成 Billion (十亿美元)
        mc_b = market_cap / 1e9
        return ScoringEngine._score_smaller_is_better(mc_b, sweet_spot=2.0, max_punish=200.0)
        
    @staticmethod
    def score_momentum(ret_6m: float) -> float:
        """
        动量因子 (6个月)：不要和死票谈恋爱，跟着大势走（Right Side of the Chart）
        半年涨 30%+ 甜蜜满分，跌破 20% 是垃圾堆
        """
        return ScoringEngine._score_larger_is_better(ret_6m, sweet_spot=0.30, min_punish=-0.20)
        
    @staticmethod
    def score_volatility(beta: float) -> float:
        """
        低波反转因子：在震荡市，偏好大盘跌他不跌（低Beta）的抗跌神票
        Beta ~ 0.5 满分，Beta > 1.5 惩罚（猴猴跳跳的票容易爆）
        """
        if beta is None or beta < 0:
            return 50.0
        # 0.8 是很稳的安全边际区间
        return ScoringEngine._score_smaller_is_better(beta, sweet_spot=0.8, max_punish=2.0)
        
    @classmethod
    def process(cls, raw_factors: Dict[str, Any]) -> Dict[str, float]:
        """
        将 `factor_extractor` 传来的字典解析打分为 0-100 面板
        """
        v = raw_factors["value"]
        q = raw_factors["quality"]
        s = raw_factors["size"]
        m = raw_factors["momentum"]
        vol = raw_factors["volatility"]
        
        scores = {
            "value_score": round(cls.score_value(v["pe_ratio"], v["pb_ratio"]), 2),
            "quality_score": round(cls.score_quality(q["current_ratio"], q["debt_to_equity"], q["profit_margin"], q["roe"]), 2),
            "size_score": round(cls.score_size(s["market_cap"]), 2),
            "momentum_score": round(cls.score_momentum(m["6m_return"]), 2),
            "volatility_score": round(cls.score_volatility(vol["beta"]), 2)
        }
        
        # 综合评分 O-Score (均等加权，或可以自定义侧重)
        # 例如：我注重价值和质量，兼顾动量
        o_score = (
            0.25 * scores["value_score"] +
            0.35 * scores["quality_score"] +
            0.20 * scores["momentum_score"] +
            0.10 * scores["size_score"] +
            0.10 * scores["volatility_score"]
        )
        scores["overall_score"] = round(o_score, 2)
        return scores
        
if __name__ == "__main__":
    from factor_extractor import extract_raw_factors
    raw = extract_raw_factors("NVDA")  # 测试高质量成长大盘股
    scores = ScoringEngine.process(raw)
    import json
    print("\n--- NVDA Multi-Factor Status ---")
    print(json.dumps(scores, indent=2))
