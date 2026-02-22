import sys
from pathlib import Path

# Add the parent directory to the path so we can import finance_news_collector
sys.path.insert(0, str(Path(__file__).parent.parent))

from crawlers.finance_news_collector import FinanceNewsCollector, FINANCE_TOPICS
from .views import (
    print_welcome, print_menu, get_menu_choice, 
    prompt_topic, prompt_keyword, show_spinner, 
    print_news_table, print_message
)

def start_api_server():
    """Starts the Flask API server."""
    print_message("正在启动 REST API 服务器... (按 Ctrl+C 停止)", "bold yellow")
    import runpy
    api_path = Path(__file__).parent.parent / "api.py"
    try:
        runpy.run_path(str(api_path), run_name="__main__")
    except KeyboardInterrupt:
        print_message("\nAPI 服务器已停止。", "bold green")

def run_cli():
    collector = FinanceNewsCollector()
    print_welcome()
    
    while True:
        print_menu()
        choice = get_menu_choice()
        
        if choice == 0:
            print_message("👋 感谢使用，再见！", "bold green")
            break
            
        elif choice == 1:
            topic = prompt_topic(list(FINANCE_TOPICS.keys()))
            with show_spinner(f"正在搜集【{topic}】的新闻..."):
                result = collector.search_topic(topic, num_results=10)
            
            print_news_table(f"主题: {topic}", result.news_items)
            path = collector.save_to_json(result)
            print_message(f"✅ 结果已保存至: {path}")
            
        elif choice == 2:
            keyword = prompt_keyword()
            with show_spinner(f"正在搜集关键词【{keyword}】的新闻..."):
                result = collector.search_news(keyword, num_results=10)
            
            print_news_table(f"搜索: {keyword}", result.news_items)
            path = collector.save_to_json(result)
            print_message(f"✅ 结果已保存至: {path}")
            
        elif choice == 3:
            print_message("🌐 即将遍历所有预定义主题，这可能需要一些时间...", "bold yellow")
            with show_spinner("正在批量搜集全网新闻..."):
                batch_results = collector.search_all_topics()
                
            print_message("✅ 批量搜集完成！各主题概览如下：")
            for topic, result in batch_results.items():
                print_news_table(f"主题: {topic}", result.news_items, limit=3)
                
            path = collector.save_batch_to_json(batch_results)
            print_message(f"✅ 汇总结果已完整保存至: {path}")
            
        elif choice == 4:
            start_api_server()

if __name__ == "__main__":
    run_cli()
