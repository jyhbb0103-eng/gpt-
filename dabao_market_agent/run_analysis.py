"""不启动网页，直接在终端测试数据获取和评分。"""

import json

from data_service import fetch_all_market_data
from market_analyzer import analyze_market


if __name__ == "__main__":
    market_data = fetch_all_market_data()
    result = analyze_market(market_data)
    print(json.dumps({
        "市场评分": result["score"],
        "市场环境": result["environment"],
        "指数趋势": result["index_trend"],
        "成交量": result["volume_state"],
        "赚钱效应": result["money_effect"],
        "短线情绪": result["short_term_emotion"],
        "评分明细": result["components"],
        "数据缺失或降级": market_data["missing_or_degraded"],
    }, ensure_ascii=False, indent=2))
