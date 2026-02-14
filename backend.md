{
  "date": "2026-02-09",
  "current_price": 64.53,
  "forecast_price": 62.928237034454945,
  "direction": "down",
  "direction_prob": 0.0005699765752069652,
  "risk_level": "medium",
  "risk_probs": {
    "low": 6.998850585659966e-05,
    "medium": 0.9996311664581299,
    "high": 0.0002988271589856595
  },
  "factor_importance": {
    "technical": 0.6201432943344116,
    "macro": 0.5081236362457275,
    "supply": 0.5529541969299316,
    "events": 0.4713454246520996
  },
  "forecast_horizon": 10,
  "forecast_curve": [
    {
      "day": 1,
      "forecast_price": 64.36800590830231
    },
    {
      "day": 2,
      "forecast_price": 64.2064184815007
    },
    {
      "day": 3,
      "forecast_price": 64.04523669871638
    },
    {
      "day": 4,
      "forecast_price": 63.884459541633284
    },
    {
      "day": 5,
      "forecast_price": 63.72408599449172
    },
    {
      "day": 6,
      "forecast_price": 63.56411504408194
    },
    {
      "day": 7,
      "forecast_price": 63.404545679737694
    },
    {
      "day": 8,
      "forecast_price": 63.24537689332992
    },
    {
      "day": 9,
      "forecast_price": 63.08660767926028
    },
    {
      "day": 10,
      "forecast_price": 62.92823703445492
    }
  ]
}
字段说明：

- date: 预测生成日期（使用最新可用数据日期）
- current_price: 当前 WTI 价格
- forecast_price: 预测窗口末的价格（由预测收益率推算）
- direction: 方向判断（up/down）
- direction_prob: 上涨概率（0-1）
- risk_level: 风险等级（low/medium/high）
- risk_probs: 风险等级概率分布
- factor_importance: 因子组贡献度（技术/宏观/供需/事件）
- forecast_horizon: 模型训练预测窗口（天）
- forecast_curve: 未来 1~N 天的价格序列（由预测窗口收益率折算成日收益率后推算）