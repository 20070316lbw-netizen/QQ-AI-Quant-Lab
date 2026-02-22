import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

# Import our project components
try:
    from crawlers.cli.app import run_cli as start_crawler
    from tradingagents.main import main as start_trading
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

console = Console()

def print_welcome():
    console.print(Panel.fit(
        "[bold cyan]🚀 AI-Quant-Lab: 智能量化智库总入口[/bold cyan]\n"
        "[dim]集成情报搜集、走势预测与智能体决策的一站式平台[/dim]",
        border_style="bright_blue"
    ))

def main_hub():
    print_welcome()
    
    while True:
        table = Table(show_header=False, box=None)
        table.add_row("[bold yellow]1[/bold yellow]", "🔍 财经新闻助手 (Crawler CLI)")
        table.add_row("[bold yellow]2[/bold yellow]", "🤖 智能体决策台 (Trading Agents)")
        table.add_row("[bold yellow]0[/bold yellow]", "🚪 退出系统")
        
        console.print("\n[bold green]请选择您要进入的模块:[/bold green]")
        console.print(table)
        
        choice = Prompt.ask("输入序号", choices=["0", "1", "2"], default="1")
        
        if choice == "0":
            console.print("[italic gray]系统已退出。[/italic gray]")
            break
        elif choice == "1":
            start_crawler()
        elif choice == "2":
            start_trading()

if __name__ == "__main__":
    main_hub()
