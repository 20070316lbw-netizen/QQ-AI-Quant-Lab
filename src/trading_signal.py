import math
from datetime import datetime
from typing import Dict, Any, Tuple, List

from core.kronos_engine import KronosEngine
from core.z_decision import compute_base_signal
from crawlers.data_gateway import DataGateway
from core.multi_factor.factor_extractor import extract_raw_factors
from core.multi_factor.scoring_engine import ScoringEngine
from core.factor_engine import FactorEngine

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
    
    # 【时空法则防线】判断是否是回测过去的日子。
    # 只要时间比现在早超过 3 天，就判定为历史舱，强制阻断无法提供历史 Point-in-Time 的免费基础面 API。
    is_historical = False
    if as_of_date:
        target_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
        if (datetime.now() - target_dt).days > 3:
            is_historical = True

    # 1. 获取纯量化特征 (Kronos + Statistical Base)
    raw_data = KronosEngine.get_raw_prediction(ticker, target_date)
    regime_strength = raw_data["regime_strength"]
    expected_return = raw_data["expected_return"]
    uncertainty = raw_data["uncertainty"]
    pred_range_pct = raw_data["predicted_range_pct"]
    pred_max = raw_data["predicted_max"]
    pred_min = raw_data["predicted_min"]
    
    # 2. Kronos 不再决定方向 —— 仅输出市场机制判断和波动门控
    # regime: STRONG_TREND_UP / STRONG_TREND_DOWN / RANGING / HIGH_VOL
    # kronos_gate: True = 当前势能贸易，False = 认为情局不明画，建议谨慎
    if abs(regime_strength) > 2.0 and uncertainty < 0.05:
        if regime_strength > 0:
            regime = "STRONG_TREND_UP"
        else:
            regime = "STRONG_TREND_DOWN"
        kronos_gate = True   # 高确信度趋势，允许信号执行
    elif uncertainty > 0.06:
        regime = "HIGH_VOL"      # 波动过大，谨慎
        kronos_gate = False
    else:
        regime = "RANGING_MIXED"  # 震荡态
        kronos_gate = True   # 不阻断信号，但强度折穿

    # 方向暂时为 PENDING，由 generate_dual_signal() 的 O-Score 排名层填充
    direction = "PENDING"


    # 3. 收集基本面/情绪调整因子
    default_sentiment, default_risk = get_llm_adjustments(ticker)
    sentiment_score = ext_sentiment if ext_sentiment is not None else default_sentiment
    risk_factor = ext_risk if ext_risk is not None else default_risk
    
    # 4. 基于波动的资金管控层 —— Kronos 作为择时门控
    # base_kronos_gate: Kronos 火力强度 tanh(|z|) 乘以波动折扣
    base_momentum_strength = math.tanh(abs(regime_strength))
    volatility_discount_factor = math.exp(-10.0 * max(0, uncertainty - 0.03))

    # Kronos 控制简化为 「是否执行门控」 + 「投资强度上限」
    # （不再乘以 O-Score 乘数，两者独立）
    kronos_position_cap = base_momentum_strength * volatility_discount_factor
    if not kronos_gate:
        kronos_position_cap *= 0.3   # 门控关闭时减小强度至 30%
    if "RANGING" in regime:
        kronos_position_cap *= 0.7   # 震荡态再进一步折口

    final_confidence = max(0.0, min(1.0, kronos_position_cap * (1 + 0.3 * sentiment_score) * (1 - risk_factor)))

    # ===== Phase 11: 引入 Fama-French 多因子选股底牌 (O-Score) =====
    # 在非 Offline 隔离时，且非历史回测穿越时，提取并打分该股票的财务多因子
    factor_scores = {}
    o_score = 50.0  # 中庸基准分 
    multi_factor_multiplier = 1.0
    
    if not DataGateway.offline_mode and not is_historical:
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
            
    # 应用 Multi-Factor 调整乘数到 final_confidence (处理 Zombie Factor 遗漏)
    final_confidence = min(1.0, final_confidence * multi_factor_multiplier)

    # 【Phase 10：财务暴雷一票否决熔断】
    # 绕开大语言模型的主观评价，直接调用 YFinance 资产负债表底层的结构化硬核数据
    # 时空壁垒：同样杜绝用明朝的剑斩前朝的官
    fundamental_risk_override = False
    if not is_historical:
        fun_metrics = DataGateway.get_fundamental_risk_metrics(ticker)
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
    
    # ── Kronos 独立信号子块（时序趋势，单股可独立使用）──────────
    kronos_position_strength = round(
        math.tanh(abs(regime_strength)) * volatility_discount_factor, 4
    )
    kronos_signal = {
        "direction":         direction,        # BUY / SELL（由 z_score 决定）
        "z_score":           round(regime_strength, 4),
        "regime":            regime,
        "expected_return":   round(expected_return, 4),
        "uncertainty":       round(uncertainty, 4),
        "position_strength": kronos_position_strength,  # 仅由 Kronos 自身决定
    }

    # ── O-Score 独立信号子块（截面质量，方向需 rank_universe() 后填充）
    #    此处仅存放 raw score，BUY/SELL 方向留 None，等批量排名后覆盖
    factor_signal_raw = {
        "direction":         None,   # 由 FactorEngine.rank_universe() 填充
        "position_strength": None,   # 同上
        "o_score":           round(o_score, 2),
        "o_score_percentile": None,
        "factor_scores":     factor_scores,
    }

    # 5. 保留完整的状态日志便于审计 (含 Phase 6 新增量化指标)
    signal_pack = {
        "ticker": ticker.upper(),
        # ── 向后兼容字段（默认保留 Kronos 方向）──────────────────
        "direction": direction,
        "regime": regime,
        "z_score": round(regime_strength, 4),
        "regime_strength": round(regime_strength, 4),
        "mean_return": round(expected_return, 4),
        "uncertainty": round(uncertainty, 4),
        "predicted_range_pct": round(pred_range_pct, 4),
        "predicted_max": round(pred_max, 2),
        "predicted_min": round(pred_min, 2),
        "adjusted_position_strength": round(final_confidence, 4),
        # ── 新增：双模块独立信号 ──────────────────────────────────
        "kronos_signal": kronos_signal,
        "factor_signal":  factor_signal_raw,
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


def generate_dual_signal(
    tickers: List[str],
    as_of_date: str = None,
    factor_top_pct: float = 0.30,
    factor_bottom_pct: float = 0.30,
    max_workers: int = 8,
) -> List[Dict[str, Any]]:
    """
    批量生成双模块信号（Kronos + O-Score 独立，横截面排名）。

    流程：
      1. 并发对每只股票调用 generate_signal()
      2. 用 FactorEngine.attach_factor_to_signals() 对全体 O-Score 做横截面排名
         → 填充 factor_signal.direction / position_strength / o_score_percentile
      3. kronos_signal.direction 保持原样（不被 O-Score 覆盖）

    每条输出记录包含：
      - direction            (Kronos 方向，向后兼容)
      - kronos_signal        (Kronos 独立子块)
      - factor_signal        (O-Score 独立子块，含横截面排名方向)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    errors  = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(generate_signal, t, as_of_date): t
            for t in tickers
        }
        for fut in as_completed(future_map):
            ticker = future_map[fut]
            try:
                sig = fut.result()
                results.append(sig)
            except Exception as e:
                errors.append({"ticker": ticker, "error": str(e)})

    # 横截面 O-Score 排名（只对成功信号做排名）
    results = FactorEngine.attach_factor_to_signals(
        results,
        top_pct=factor_top_pct,
        bottom_pct=factor_bottom_pct,
    )

    # 附加失败记录
    for err in errors:
        results.append({"ticker": err["ticker"], "error": err["error"],
                        "kronos_signal": None, "factor_signal": None})

    return results

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
