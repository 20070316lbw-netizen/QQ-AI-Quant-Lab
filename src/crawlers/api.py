from flask import Flask, request, jsonify
from finance_news_collector.base import FINANCE_TOPICS, NewsItem
from finance_news_collector.collector import FinanceNewsCollector

app = Flask(__name__)
collector = FinanceNewsCollector()

@app.route('/api/topics', methods=['GET'])
def get_topics():
    """获取所有财经主题"""
    return jsonify(list(FINANCE_TOPICS.keys()))

@app.route('/api/news', methods=['GET'])
def get_news():
    """搜索新闻接口"""
    topic = request.args.get('topic')
    keyword = request.args.get('keyword')
    num = int(request.args.get('num', 10))
    days = request.args.get('days')
    days = int(days) if days else None

    if topic:
        result = collector.search_topic(topic, num_results=num, recency_days=days)
    elif keyword:
        result = collector.search_news(keyword, num_results=num, recency_days=days)
    else:
        return jsonify({"error": "Missing 'topic' or 'keyword' parameter"}), 400

    return jsonify(result.to_dict())

if __name__ == '__main__':
    print("🚀 Crawler API is running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)
