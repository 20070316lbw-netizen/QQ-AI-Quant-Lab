import math
from datetime import datetime
from typing import Dict, Any, Tuple

from core.kronos_engine import KronosEngine
from core.z_decision import compute_base_signal
from crawlers.data_gateway import DataGateway
from core.multi_factor.factor_extractor import extract_raw_factors
from core.multi_factor.scoring_engine import ScoringEngine

def get_llm_adjustments(ticker: str) -> Tuple[float, float]:
    """
    [Phase 2 留白]
    在独立运行时，回退的默认情绪与风险评估。
    """
    return 0.0, 0.3

def generate_signal(ticker: str, as_of_date: str = None, ext_sentiment: float = None, ext_risk: float = None) -> Dict[str, Any]:
    """
    生成高度结构化、基于 Z-Score 引擎与 NLP 辅助降权的交易信号字典。
    
    :param ticker: 公司/代币的大写代号，如 AAPL
    :param as_of_date: 历史模拟回测的截断点 YYYY-MM-DD，留空则为今日
    :param ext_sentiment: 外部注入的市场情绪 (-1.0 到 1.0)
    :param ext_risk: 外部注入的市场风险系数 (0.0 到 1.0)
    :return: 标准量化交易信令 JSON 结构
    """
    target_date = as_of_date if as_of_date else datetime.now().strftime("%Y-%m-%d")
    
    # 1. 获取纯量化特征 (Kronos + Statistical Base)
    raw_data = KronosEngine.get_raw_prediction(ticker, target_date)
    regime_strength = raw_data["regime_strength"]
    expected_return = raw_data["expected_return"]
    uncertainty = raw_data["uncertainty"]
    pred_range_pct = raw_data["predicted_range_pct"]
    pred_max = raw_data["predicted_max"]
    pred_min = raw_data["predicted_min"]
    
    # 2. 状态(Regime)判定与方向仲裁
    # 阈值 0.5 依然作为强弱分界，但不再直接输出毫无意义的 HOLD。
    # - 强趋势状态 (Strong Regime): 顺势操作
    # - 震荡收敛状态 (Ranging Regime): 放弃方向预测或准备均值回归
    if regime_strength > 0.5:
        direction = "BUY"
        regime = "STRONG_TREND_UP"
    elif regime_strength < -0.5:
        direction = "SELL"
        regime = "STRONG_TREND_DOWN"
    else:
        # 当强度不足时，默认方向根据均值正负，标设为震荡态
        direction = "BUY" if expected_return > 0 else "SELL"
        regime = "RANGING_MIXED"
    
    # 3. 收集基本面/情绪调整因子
    default_sentiment, default_risk = get_llm_adjustments(ticker)
    sentiment_score = ext_sentiment if ext_sentiment is not None else default_sentiment
    risk_factor = ext_risk if ext_risk is not None else default_risk
    
    # 4. 基于波动的资金管控层 (Volatility-based Position Sizing)
    # 基础动量分依然是强度 tanh
    base_momentum_strength = math.tanh(abs(regime_strength))
    
    # 【核心！】预测波动极大时（例如预测标准差>5%），必须缩减杠杆与头寸以管控风险
    volatility_discount_factor = math.exp(-10.0 * max(0, uncertainty - 0.03)) 
    
    # ===== Phase 11: 引入 Fama-French 多因子选股底牌 (O-Score) =====
    # 在非 Offline 隔离时，提取并打分该股票的财务多因子
    factor_scores = {}
    o_score = 50.0  # 中庸基准分 
    multi_factor_multiplier = 1.0
    
    if not DataGateway.offline_mode:
        try:
            raw_factors = extract_raw_factors(ticker)
            factor_scores = ScoringEngine.process(raw_factors)
            o_score = factor_scores.get("overall_score", 50.0)
            
            # 因子分与仓位乘数映射关系 (Factor to Multiplier)
            # O-Score 在 [0, 100] 分之间，50 分为 1x 倍数不增不减。
            # 如果是个破烂票 (O < 30) -> 大减仓 甚至是腰斩
            # 如果是个金手指 (O > 70) -> 仓位微提
            multi_factor_multiplier = 0.5 + (o_score / 100.0) * 1.0 # 满分100 = 1.5倍；0分 = 0.5倍锁仓
            
        except Exception as e:
            print(f"Warning: Multi-Factor extraction failed: {e}")
            
    # 融合：动量 * 波动折扣 * 因子乘数 * 情绪放大 * 风险惩罚
    adjusted_strength = base_momentum_strength * volatility_discount_factor * multi_factor_multiplier * (1 + 0.3 * sentiment_score) * (1 - risk_factor)
    
    # 属于震荡行情时，主观降低其置信度上限
    if "RANGING" in regime:
        adjusted_strength *= 0.5
    
    final_confidence = max(0.0, min(1.0, adjusted_strength))
    
    # 【Phase 10：财务暴雷一票否决熔断】
    # 绕开大语言模型的主观评价，直接调用 YFinance 资产负债表底层的结构化硬核数据
    fun_metrics = DataGateway.get_fundamental_risk_metrics(ticker)
    fundamental_risk_override = False
    if fun_metrics.get("is_valid", False):
        debt_to_eq = fun_metrics.get("debtToEquity", 0.0)
        curr_ratio = fun_metrics.get("currentRatio", 1.0)
        
        # 极硬性条件：杠杆被吹成泡沫(>3倍) 并且 短期用于救火的流动现金枯竭(<0.8)
        if debt_to_eq > 3.0 and curr_ratio < 0.8:
            fundamental_risk_override = True
            from rich.console import Console
            Console().print(f"[bold red on white]🚨 基本面极度崩盘预警: {ticker} 陷入债务死局! (Debt/Eq={debt_to_eq:.2f}, 缺钱率 CurRatio={curr_ratio:.2f})[/bold red on white]")
            Console().print("[bold red]⛔ 无论 K 线趋势多好或 NLP 如何吹捧，系统底层强制一票否决归零该票仓位！[/bold red]")
            
            final_confidence = 0.0
            regime = "FUNDAMENTAL_BUST_OVERRIDE"
            direction = "CRASH_SELL"
    
    # 5. 保留完整的状态日志便于审计 (含 Phase 6 新增量化指标)
    signal_pack = {
        "ticker": ticker.upper(),
        "direction": direction,
        "regime": regime,
        "z_score": round(regime_strength, 4), # 为了兼容旧表结构暂时保留字段
        "regime_strength": round(regime_strength, 4),
        "mean_return": round(expected_return, 4),
        "uncertainty": round(uncertainty, 4),
        "predicted_range_pct": round(pred_range_pct, 4),
        "predicted_max": round(pred_max, 2),
        "predicted_min": round(pred_min, 2),
        "adjusted_position_strength": round(final_confidence, 4),
        "metadata": {
            "model": "kronos-v1-foundation",
            "timestamp": f"{as_of_date}T23:59:59Z" if as_of_date else (datetime.now().isoformat() + "Z"),
            "sentiment_score": round(sentiment_score, 4),
            "risk_factor": round(risk_factor, 4),
            "base_strength": round(base_momentum_strength, 4),
            "volatility_discount": round(volatility_discount_factor, 4),
            "fundamental_bust_triggered": fundamental_risk_override,
            "multi_factor_o_score": round(o_score, 2),
            "multi_factor_multiplier": round(multi_factor_multiplier, 3),
            "factor_scores": factor_scores
        }
    }
    
    # 5. 落盘到不可篡改的日志系统中用于回测
    try:
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from utils.logger_sys import global_logger
        global_logger.log_decision(signal_pack)
    except Exception as e:
        print(f"Warning: Failed to write decision log: {e}")
    
    return signal_pack

if __name__ == "__main__":
    # 极简调试入口
    print("Testing generate_signal API for AAPL...")
    try:
        import json
        sg = generate_signal("AAPL")
        print(json.dumps(sg, indent=2, ensure_ascii=False))
    except Exception as e:
        import traceback
        traceback.print_exc()
