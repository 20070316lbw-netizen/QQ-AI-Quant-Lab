import os
import sys
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

def test_formatted_output():
    ticker = "AAPL"
    today = datetime.now().strftime("%Y-%m-%d")
    
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "ollama"
    config["backend_url"] = "http://localhost:11434"
    config["deep_think_llm"] = "qwen2.5:3b"
    config["quick_think_llm"] = "qwen2.5:3b"
    
    print(f"Testing formatted output for {ticker}...")
    ta = TradingAgentsGraph(debug=False, config=config, test_mode=True)
    final_state, _ = ta.propagate(ticker, today)
    
    print("\n--- FINAL DECISION OUTPUT ---")
    decision = final_state.get("final_trade_decision", "N/A")
    print(decision)
    print("----------------------------")

if __name__ == "__main__":
    test_formatted_output()
