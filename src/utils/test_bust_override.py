import sys
import os
import json

# Ensure src is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from crawlers.data_gateway import DataGateway
from trading_signal import generate_signal

# 1. 挂钩（Mock）DataGateway 的基本面接口，模拟一个负债爆雷的恒大式企业
def mocked_get_fundamental_risk_metrics(ticker: str) -> dict:
    return {
        "debtToEquity": 5.2,   # 负债是权益的5.2倍，极度危险 (> 3.0)
        "currentRatio": 0.5,   # 手里的现金连短期债务的一半都还不上 (< 0.8)
        "freeCashflow": -100000000,
        "is_valid": True
    }

# 狸猫换太子
DataGateway.get_fundamental_risk_metrics = mocked_get_fundamental_risk_metrics

print("\n🚨 [TEST START] 尝试针对满身债务的虚假标的生成量化信号...")
print("我们在测试桩中赋予了这家公司 Debt/Eq=5.2 以及 CurRatio=0.5 的绝境财务报表。")

# 2. 注入外部极度狂热的多头情绪，测试诱多时风控的骨气
# 我们使用 AAPL 来成功通过前面的 K 线拉取，但背后的财报已经被我们掉包成了破产水平
signal_pack = generate_signal("AAPL", ext_sentiment=0.9, ext_risk=0.1)

print("\n--- 最终量化信令包 ---")
print(json.dumps(signal_pack, indent=2, ensure_ascii=False))

if signal_pack["adjusted_position_strength"] == 0.0 and signal_pack["regime"] == "FUNDAMENTAL_BUST_OVERRIDE":
    print("\n✅ 测试通过：虽然 NLP 和趋势可能极度看多，但是硬指标风控成功阻击了这次高危交易。本金毫发无损！")
else:
    print("\n❌ 测试失败：风控未能拦住此次高负债交易。")
