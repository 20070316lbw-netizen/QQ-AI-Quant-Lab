import sys
import os
import json

curr_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(curr_dir, "../.."))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from src.trading_signal import generate_signal

class PortfolioAllocator:
    """
    智能投资组合优化器 (Risk Parity + O-Score)
    根据输入的股票组，调用底层信令获取 O-Score 与 不确定性，
    计算避险最优的饼图拆分比例。
    """
    
    @staticmethod
    def allocate(tickers: list, as_of_date: str = None) -> dict:
        results = {}
        valid_tickets = []
        raw_weights = {}
        total_raw_weight = 0.0
        
        for ticker in tickers:
            ticker = ticker.strip().upper()
            if not ticker: continue
            
            try:
                # 调取生成信令，获取 O-Score 和 Uncertainty，或者暴雷封杀
                signal = generate_signal(ticker, as_of_date=as_of_date)
                meta = signal['metadata']
                
                if meta.get('fundamental_bust_triggered', False):
                    # 极度危险资产直接一票否决
                    results[ticker] = {
                        "status": "BUST",
                        "weight": 0.0,
                        "o_score": meta.get('multi_factor_o_score', 0),
                        "uncertainty": signal['uncertainty'],
                        "reason": "财务指标严重恶化或破产预警，系统强制摘除。"
                    }
                    continue
                    
                o_score = meta.get('multi_factor_o_score', 50.0)
                uncertainty = signal['uncertainty']
                
                # 核心配资算法：类风险平价（Risk Parity）结合多因子护城河
                # 分子是护城河得分（越优质权重越大），分母是波动风险（越动荡权重越小）
                # + 0.005 是为了防止不确定性太小导致除以 0 的极值放大
                w = max(0, o_score) / (uncertainty + 0.005)
                
                raw_weights[ticker] = w
                total_raw_weight += w
                valid_tickets.append(ticker)
                
                results[ticker] = {
                    "status": "OK",
                    "raw_weight": w,
                    "o_score": o_score,
                    "uncertainty": uncertainty,
                    "regime": signal['regime']
                }
            except Exception as e:
                 results[ticker] = {
                    "status": "ERROR",
                    "weight": 0.0,
                    "reason": str(e)
                 }

        # 归一化分配 100% 仓位
        if total_raw_weight > 0:
            for t in valid_tickets:
                w_pct = raw_weights[t] / total_raw_weight
                results[t]['weight'] = w_pct
        else:
            # 万一全部计算失败或都是 0，则平分或皆 0
            for t in valid_tickets:
                results[t]['weight'] = 0.0
                
        return {
            "allocation": results,
            "valid_count": len(valid_tickets),
            "total_evaluated": len(tickers)
        }

if __name__ == "__main__":
    test_pool = ["AAPL", "TSLA", "KO", "600519.SS"]
    print(f"Testing Portfolio Allocator with {test_pool}")
    out = PortfolioAllocator.allocate(test_pool)
    print(json.dumps(out, indent=2, ensure_ascii=False))
