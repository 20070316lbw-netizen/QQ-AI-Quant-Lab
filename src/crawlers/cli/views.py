from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import questionary
import time

console = Console()

def print_welcome():
    console.print(Panel("[bold cyan]🚀 欢迎使用财经新闻自动搜集交互式终端[/bold cyan]\n[dim]支持全自动化采集、主题精搜与本地 API 运行[/dim]", expand=False, border_style="cyan"))

def print_menu():
    # Only used if some legacy code calls it, otherwise app.py handles selection directly
    pass

def get_menu_choice():
    choice = questionary.select(
        "请选择一项操作:",
        choices=[
            questionary.Choice("🔍 按主题搜集新闻 (列出内置主题)", value=1),
            questionary.Choice("⌨️ 按关键词搜集新闻", value=2),
            questionary.Choice("🌐 一键汇编所有主题 (搜集全量信息并保存)", value=3),
            questionary.Choice("🚀 启动 REST API 服务器", value=4),
            questionary.Choice("🚪 退出程序", value=0)
        ],
        style=questionary.Style([
            ("selected", "fg:yellow bold"),
            ("pointer", "fg:yellow bold"),
            ("highlighted", "fg:yellow bold"),
        ]),
        instruction="\n- 按上/下方向键切换，按回车键进入"
    ).ask()
    
    return choice if choice is not None else 0

def prompt_topic(available_topics):
    choice = questionary.select(
        "可用主题 (方向键选择):",
        choices=[
            questionary.Choice(topic, value=topic) for topic in available_topics
        ],
        style=questionary.Style([
            ("selected", "fg:cyan bold"),
            ("pointer", "fg:cyan bold"),
            ("highlighted", "fg:cyan bold"),
        ])
    ).ask()
    
    # Fallback equivalent
    return choice if choice is not None else available_topics[0]

def prompt_keyword():
    word = questionary.text(
        "请输入搜索关键词:",
        style=questionary.Style([("text", "fg:green")])
    ).ask()
    return word if word else "AI"

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
