import sys
import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import our project components
try:
    from crawlers.cli.app import run_cli as start_crawler
    from tradingagents.main import main as start_trading
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    from tradingagents.default_config import DEFAULT_CONFIG
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

console = Console()

def print_welcome():
    console.print(Panel.fit(
        "[bold cyan]🚀 AI-Quant-Lab: 智能量化智库总入口 (v3)[/bold cyan]\n"
        "[dim]Agent-Centric Architecture: 智能调度搜集、预测与研判的一站式平台[/dim]",
        border_style="bright_blue"
    ))

def run_agentic_flow():
    """全自动执行端到端的研报生成链路"""
    console.print(Panel("[bold yellow]🤖 智能体大模型证券分析终端 v3[/bold yellow]", border_style="yellow"))
    ticker = Prompt.ask("👉 请输入您想要分析的股票/标的代码 (如 AAPL, NVDA, BABA)", default="AAPL")
    
    # 自动获取今天起算的一个合理预测节点 (默认为今天)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "ollama"
    config["backend_url"] = "http://localhost:11434"
    config["deep_think_llm"] = "qwen2.5:3b"
    config["quick_think_llm"] = "qwen2.5:3b"
    config["max_debate_rounds"] = 1
    
    console.print(f"\n[bold cyan]正在启动量化分析智能体集群... (标的: {ticker}, 基准日: {today})[/bold cyan]")
    try:
        ta = TradingAgentsGraph(debug=True, config=config)
        
        # 执行图传播 (包含爬虫数据拉取和 Kronos 预测)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Agent 正在深度思考并跨模块调度资源...", total=None)
            final_state, decision = ta.propagate(ticker, today)
        
        console.print("\n[bold green]✅ 分析任务已完成！[/bold green]")
        console.print(Panel(decision, title=f"最终分析意见: {ticker}", border_style="green"))
            
    except Exception as e:
        console.print(f"\n[bold red]❌ 智能体运行过程中发生故障:[/bold red] {str(e)}")
        
    Prompt.ask("\n按回车键返回主菜单...")

def main_hub():
    print_welcome()
    
    while True:
        table = Table(show_header=False, box=None)
        table.add_row("[bold yellow]1[/bold yellow]", "🔍 财经新闻助手 (Crawler CLI - 单独抓数据)")
        table.add_row("[bold yellow]2[/bold yellow]", "🤖 智能体研究员 (全自动运行端到端行情研判)")
        table.add_row("[bold yellow]3[/bold yellow]", "⚙️  执行 Agent 演示脚本 (TradingAgents main.py)")
        table.add_row("[bold yellow]0[/bold yellow]", "🚪 退出系统")
        
        console.print("\n[bold green]请选择您的操作模式:[/bold green]")
        console.print(table)
        
        choice = Prompt.ask("输入序号", choices=["0", "1", "2", "3"], default="2")
        
        if choice == "0":
            console.print("[italic gray]系统已退出。[/italic gray]")
            break
        elif choice == "1":
            start_crawler()
        elif choice == "2":
            run_agentic_flow()
        elif choice == "3":
            start_trading()

if __name__ == "__main__":
    main_hub()
