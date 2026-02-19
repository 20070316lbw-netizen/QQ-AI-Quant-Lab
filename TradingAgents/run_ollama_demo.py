from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create a custom config for Ollama
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "ollama"
config["backend_url"] = "http://localhost:11434"
config["deep_think_llm"] = "qwen2.5:3b"
config["quick_think_llm"] = "qwen2.5:3b"
config["max_debate_rounds"] = 1

# Configure data vendors (default uses yfinance, no extra API keys needed)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",           # Options: alpha_vantage, yfinance
    "technical_indicators": "yfinance",      # Options: alpha_vantage, yfinance
    "fundamental_data": "yfinance",          # Options: alpha_vantage, yfinance
    "news_data": "yfinance",                 # Options: alpha_vantage, yfinance
}

print(f"Starting TradingAgents with Ollama at {config['backend_url']} and model {config['deep_think_llm']}...")

try:
    # Initialize with custom config
    ta = TradingAgentsGraph(debug=True, config=config)

    # forward propagate for a sample stock
    ticker = "NVDA"
    date = "2024-05-10"
    print(f"Running propagation for {ticker} on {date}...")
    _, decision = ta.propagate(ticker, date)
    print("\nTrading Decision:")
    print(decision)
except Exception as e:
    print(f"\nAn error occurred during verification: {e}")
    print("This might be due to Ollama not running or the model not being pulled.")
    print("Recommendation: Run 'ollama pull deepseek-r1:1.5b' and ensure Ollama is active.")
