import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

def test_localization():
    print("开始验证汉化效果...")
    
    config = DEFAULT_CONFIG.copy()
    # 强制开启 debug 模式以查看流式中文日志
    config["llm_provider"] = "ollama"
    config["backend_url"] = "http://localhost:11434"
    config["deep_think_llm"] = "qwen2.5:3b"
    config["quick_think_llm"] = "qwen2.5:3b"
    config["max_debate_rounds"] = 1
    
    ticker = "NVDA"
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        ta = TradingAgentsGraph(debug=True, config=config)
        print(f"正在分析 {ticker}...")
        
        # 只跑 1 轮 debate 以节省时间
        final_state, decision = ta.propagate(ticker, today)
        
        print("\n" + "="*50)
        print("【验证成功】最终决策输出:")
        print(decision)
        print("="*50)
        
        # 检查研报语言
        print("\n检查市场报告语言片段:")
        print(final_state.get('market_report', '未生成')[:200])
        
    except Exception as e:
        print(f"验证失败: {e}")

if __name__ == "__main__":
    test_localization()
