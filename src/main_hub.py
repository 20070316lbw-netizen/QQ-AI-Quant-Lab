import sys
import datetime
import questionary
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
    from tradingagents.utils.llm_deploy_helper import deploy_assistant_ui
    from tui_app import AlphaGenomeApp  # Alpha Genome TUI
except ImportError as e:
    print(f"Error importing modules: {e}")
    # Don't exit if core modules are missing, but warn
    pass

console = Console()

def print_welcome():
    console.print(Panel.fit(
        "[bold cyan]🚀 AI-Quant-Lab: 智能量化智库总入口 (v3)[/bold cyan]\n"
        "[dim]Agent-Centric Architecture: 智能调度搜集、预测与研判的一站式平台[/dim]",
        border_style="bright_blue"
    ))

def run_alpha_genome_tui():
    """启动 Alpha Genome 专业投研终端"""
    console.print("[bold cyan]正在启动 Alpha Genome TUI...[/bold cyan]")
    try:
        app = AlphaGenomeApp()
        app.run()
    except Exception as e:
        console.print(f"[bold red]❌ TUI 启动失败: {e}[/]")
        Prompt.ask("\n按回车键返回主菜单...")

def run_agentic_flow():
    """全自动执行端到端的研报生成链路"""
    console.print(Panel("[bold yellow]🤖 智能体大模型证券分析终端 v3[/bold yellow]", border_style="yellow"))
    ticker = Prompt.ask("👉 请输入您想要分析的股票/标的代码 (如 AAPL, NVDA, BABA)", default="AAPL")
    
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
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Agent 正在深度思考并跨模块调度资源...", total=None)
            final_state, decision = ta.propagate(ticker, today)
        console.print("\n[bold green]✅ 分析任务已完成！[/bold green]")
        console.print(Panel(decision, title=f"最终分析意见: {ticker}", border_style="green"))
    except Exception as e:
        console.print(f"\n[bold red]❌ 智能体运行过程中发生故障:[/bold red] {str(e)}")
    Prompt.ask("\n按回车键返回主菜单...")

def run_legacy_verdict():
    """运行旧版 Kronos + O-Score 综合判决 (整合自 main.py)"""
    ticker = Prompt.ask("👉 请输入待裁决资产代码 (如 AAPL, 600519.SS)", default="AAPL")
    ticker = ticker.strip().upper()
    console.print(f"\n[bold green]正在调用 Kronos-V2 联合审查流水线...[/bold green]")
    try:
        from trading_signal import generate_signal
        import json
        signal = generate_signal(ticker)
        console.print(Panel(json.dumps(signal, indent=2, ensure_ascii=False), title=f"Legacy Verdict: {ticker}", border_style="yellow"))
    except Exception as e:
        console.print(f"[bold red]❌ 裁决执行失败: {e}[/]")
    Prompt.ask("\n按回车键返回主菜单...")

def run_kronos_test_flow():
    """孤立测试 Kronos 模型的高级实验流"""
    console.print(Panel("[bold magenta]🧪 Kronos Foundations: 纯量化时序预测测试 (V7.0)[/bold magenta]", border_style="magenta"))
    ticker = Prompt.ask("👉 请输入测试标的代码 (如 AAPL, TSLA)", default="AAPL")
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "ollama"
    config["backend_url"] = "http://localhost:11434"
    
    console.print(f"\n[bold magenta]正在启动隔离实验环境... (噪音过滤: ON, 预测模型: Kronos-v1)[/bold magenta]")
    try:
        ta = TradingAgentsGraph(debug=True, config=config, test_mode=True)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="正在计算时序预测曲线并映射交易信号...", total=None)
            final_state, stripped_decision = ta.propagate(ticker, today)
        console.print("\n[bold green]✅ 孤立测试完成！[/bold green]")
        full_report = final_state.get("final_trade_decision", stripped_decision)
        console.print(Panel(full_report, title=f"Kronos 深度量化报告: {ticker}", border_style="magenta"))
    except Exception as e:
        console.print(f"\n[bold red]❌ 实验运行故障:[/bold red] {str(e)}")
    Prompt.ask("\n按回车键返回主菜单...")

def main_hub():
    print_welcome()
    
    while True:
        choice = questionary.select(
            "请选择您的操作模式 (使用上下方向键选择，回车确认):",
            choices=[
                questionary.Choice("🧬 Alpha Genome TUI (专业基因投研终端)", value="alpha_tui"),
                questionary.Choice("🤖 智能体研究员 (全自动运行端到端行情研判)", value="agent"),
                questionary.Choice("⚖️  Kronos 综合裁定 (整合版实盘判决逻辑)", value="legacy_verdict"),
                questionary.Choice("🧪 Kronos 孤立性测试模式 (纯量化模型验证)", value="kronos_test"),
                questionary.Choice("🔍 财经新闻助手 (Crawler CLI - 单独抓数据)", value="crawler"),
                questionary.Choice("⚙️  执行 Agent 演示脚本 (TradingAgents main.py)", value="demo"),
                questionary.Choice("🛠️  LLM 部署助手 (本地模型安装与检测)", value="llm_tool"),
                questionary.Choice("🚪 退出系统", value="exit")
            ],
            style=questionary.Style([
                ("selected", "fg:cyan bold"),
                ("pointer", "fg:cyan bold"),
                ("highlighted", "fg:cyan bold"),
            ]),
            instruction="\n按上/下方向键切换，按回车键进入"
        ).ask()
        
        if choice == "exit" or choice is None:
            console.print("[italic gray]系统已退出。[/italic gray]")
            break
        elif choice == "alpha_tui":
            run_alpha_genome_tui()
        elif choice == "legacy_verdict":
            run_legacy_verdict()
        elif choice == "crawler":
            start_crawler()
        elif choice == "agent":
            run_agentic_flow()
        elif choice == "kronos_test":
            run_kronos_test_flow()
        elif choice == "demo":
            start_trading()
        elif choice == "llm_tool":
            deploy_assistant_ui()
            Prompt.ask("\n按回车键返回主菜单...")

if __name__ == "__main__":
    main_hub()
