import sys
import os
import json

curr_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(curr_dir, ".."))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from trading_signal import generate_signal
from core.multi_factor.factor_extractor import extract_raw_factors

def test_ashare(ticker: str, name: str):
    print(f"\n==============================================")
    print(f"🇨🇳 开始测试 A 股兼容性: {name} ({ticker})")
    print(f"==============================================")
    
    # 1. 探查底层多因子裸数据对于 A 股的缺失度
    print("\n[第一步] 探查 YFinance 对于该 A 股的因子提供情况 (Factor Extractor)")
    factors = extract_raw_factors(ticker)
    print(json.dumps(factors, indent=2, ensure_ascii=False))
    
    # 2. 实盘量化主脑信号生成（贯穿 Kronos K 线预测 + 因子转化系统）
    print(f"\n[第二步] 生成复合端到端交易信令 (Kronos V2 + O-Score)")
    try:
        # A 股往往自带强烈的政策市和动量反转，这里就不 mock 额外的 NLP 情绪了
        signal = generate_signal(ticker)
        print("\n✅ 信令生成成功！最终回包：")
        print(json.dumps(signal, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"\n❌ A 股 ({ticker}) 信令生成失败, 错误堆栈: {e}")

if __name__ == "__main__":
    # 1. 测试上海证券交易所 (Shanghai Stock Exchange - .SS) 绝对龙头：贵州茅台
    test_ashare("600519.SS", "贵州茅台")
    
    # 2. 测试深圳证券交易所 (Shenzhen Stock Exchange - .SZ) 银行权重：平安银行
    test_ashare("000001.SZ", "平安银行")
