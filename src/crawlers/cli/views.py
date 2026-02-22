from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

console = Console()

def print_welcome():
    console.print(Panel("[bold cyan]🚀 欢迎使用财经新闻自动搜集交互式终端[/bold cyan]\n[dim]支持全自动化采集、主题精搜与本地 API 运行[/dim]", expand=False, border_style="cyan"))

def print_menu():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("[bold yellow]1[/bold yellow]", "🔍 按主题搜集新闻 (列出内置主题)")
    table.add_row("[bold yellow]2[/bold yellow]", "⌨️ 按关键词搜集新闻")
    table.add_row("[bold yellow]3[/bold yellow]", "🌐 一键汇编所有主题 (搜集全量信息并保存)")
    table.add_row("[bold yellow]4[/bold yellow]", "🚀 启动 REST API 服务器")
    table.add_row("[bold yellow]0[/bold yellow]", "🚪 退出程序")
    console.print("\n[bold green]请选择一项操作:[/bold green]")
    console.print(table)

def get_menu_choice():
    while True:
        choice = Prompt.ask("[bold green]请输入序号[0-4][/bold green]", default="1")
        if choice in ["0", "1", "2", "3", "4"]:
            return int(choice)
        console.print("[red]❌ 无效输入，请重新输入。[/red]")

def prompt_topic(available_topics):
    console.print("\n[bold cyan]可用主题:[/bold cyan]")
    for i, topic in enumerate(available_topics, 1):
        console.print(f"[{i}] {topic}")
    
    while True:
        idx = IntPrompt.ask("[bold green]请选择主题序号[/bold green]", default=1)
        if 1 <= idx <= len(available_topics):
            return available_topics[idx - 1]
        console.print("[red]❌ 无效序号，请重新输入。[/red]")

def prompt_keyword():
    return Prompt.ask("\n[bold green]请输入搜索关键词[/bold green]")

def show_spinner(task_desc="正在搜索中..."):
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    )

def print_news_table(title, items, limit=10):
    table = Table(title=f"[bold]📰 {title}[/bold]", show_lines=True, header_style="bold magenta")
    table.add_column("序号", style="dim", width=4)
    table.add_column("标题", style="cyan", width=40)
    table.add_column("来源", style="green", width=15)
    table.add_column("日期", style="yellow", width=12)
    
    for i, item in enumerate(items[:limit], 1):
        table.add_row(str(i), item.title, item.source, item.date)
        
    console.print(table)
    if len(items) > limit:
        console.print(f"[dim]...还有 {len(items) - limit} 条新闻未显示，详细内容请查看保存的 JSON 文件。[/dim]")

def print_message(msg, style="green"):
    console.print(f"[{style}]{msg}[/{style}]")
