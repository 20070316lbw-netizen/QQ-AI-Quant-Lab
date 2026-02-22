from .graph.trading_graph import TradingAgentsGraph
from .default_config import DEFAULT_CONFIG

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create a custom config
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "ollama"
config["backend_url"] = "http://localhost:11434"
config["deep_think_llm"] = "qwen2.5:3b"
config["quick_think_llm"] = "qwen2.5:3b"
config["max_debate_rounds"] = 1

    # configuration is simpler for v3


def main():
    """初始化并运行交易智能体"""
    ta = TradingAgentsGraph(debug=True, config=config)
    # 执行决策预测
    _, decision = ta.propagate("NVDA", "2026-02-19")
    print(decision)

if __name__ == '__main__':
    main()
