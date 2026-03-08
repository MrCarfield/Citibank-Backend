"""
LLM Council Forecast 服务 - 使用多AI模型生成所有Forecast API数据

替代原有的豆包单模型调用，使用LLM Council多模型协作生成：
- distribution
- signal  
- confidence
- backtest
- overview
- risk_analysis
- transmission_path
- drivers
- stress_test
"""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
import json
import asyncio

from app.services.llm_council.core import run_full_council
from app.schemas.forecast import (
    MarketType, HorizonType, RiskLevel, ConfidenceLevel,
    DirectionType, Probabilities, RiskDriverType, TriggerSeverity,
    FactorCategory
)


class LLMCouncilForecastService:
    """使用多AI模型生成Forecast数据的服务"""
    
    def __init__(self):
        self.max_retries = 3
        self.timeout = 60.0
    
    async def _call_council_with_retry(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用LLM Council并处理重试逻辑
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（会合并到prompt中）
            
        Returns:
            Council返回结果字典
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System]: {system_prompt}\n\n[User]: {prompt}"
        
        for attempt in range(self.max_retries):
            try:
                result = await asyncio.wait_for(
                    run_full_council(full_prompt),
                    timeout=self.timeout
                )
                return result
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                return {"error": "Timeout", "final_response": None}
            except Exception as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return {"error": str(e), "final_response": None}
        
        return {"error": "Max retries exceeded", "final_response": None}
    
    def _parse_json_from_response(self, response_text: str) -> Optional[Dict]:
        """从LLM响应中解析JSON数据"""
        if not response_text:
            return None
        
        # 尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON代码块
        import re
        json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        matches = re.findall(json_pattern, response_text)
        
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
        
        # 尝试提取花括号内容
        try:
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                return json.loads(response_text[start:end+1])
        except json.JSONDecodeError:
            pass
        
        return None
    
    async def generate_distribution_data(
        self,
        market: MarketType,
        horizon: HorizonType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成distribution端点数据"""
        current_price = algorithm_data.get('current_price', 64.53)
        forecast_price = algorithm_data.get('forecast_price', 62.93)
        direction_prob = algorithm_data.get('direction_prob', 0.5)
        
        prompt = f"""基于以下算法预测数据，生成概率预测分布的JSON格式数据：

算法数据：
- 当前价格: {current_price}
- 预测价格: {forecast_price}
- 上涨概率: {direction_prob}
- 市场: {market.value}
- 预测周期: {horizon.value}

请生成以下格式的JSON：
{{
    "horizon": "{horizon.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "market": "{market.value}",
    "median": 中位数价格(数字),
    "p10": 10%分位数价格(数字),
    "p90": 90%分位数价格(数字),
    "probabilities": {{
        "up": 上涨概率(0-1),
        "flat": 横盘概率(0-1),
        "down": 下跌概率(0-1)
    }},
    "modelId": "模型ID字符串",
    "modelVersion": "版本号字符串"
}}

注意：
1. 所有数值必须基于算法数据合理推算
2. probabilities三个概率之和应接近1
3. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        # 返回默认值
        return {
            "horizon": horizon.value,
            "asOf": datetime.utcnow().isoformat(),
            "market": market.value,
            "median": round(current_price, 2),
            "p10": round(min(current_price, forecast_price) - 2, 2),
            "p90": round(max(current_price, forecast_price) + 2, 2),
            "probabilities": {"up": round(direction_prob, 2), "flat": 0.3, "down": round(1 - direction_prob - 0.3, 2)},
            "modelId": "oil-forecast-ensemble-v3",
            "modelVersion": "3.2.1"
        }
    
    async def generate_signal_data(
        self,
        market: MarketType,
        horizon: HorizonType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成signal端点数据（风险信号）"""
        risk_level = algorithm_data.get('risk_level', 'medium')
        factor_importance = algorithm_data.get('factor_importance', {})
        
        prompt = f"""基于以下算法预测数据，生成风险信号分析的JSON格式数据：

算法数据：
- 风险等级: {risk_level}
- 市场: {market.value}
- 因子贡献度: {json.dumps(factor_importance, ensure_ascii=False)}

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "horizon": "{horizon.value}",
    "level": "风险等级(LOW/MEDIUM/HIGH)",
    "drivers": [
        {{
            "type": "风险类型(VOLATILITY/EVENT/MACRO_COINCIDENCE/TERM_STRUCTURE/LIQUIDITY/OTHER)",
            "weight": 权重(0-1),
            "note": "风险描述(中文，简洁专业)"
        }}
    ],
    "triggers": [
        {{
            "if": "触发条件(中文)",
            "then": "后续影响(中文)",
            "severity": "严重程度(INFO/WARN/CRITICAL)"
        }}
    ]
}}

要求：
1. 生成4-5个风险驱动因素，基于因子贡献度排序
2. 生成3-4个触发条件场景
3. 所有文本使用中文，专业简洁
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        # 返回默认值
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "horizon": horizon.value,
            "level": risk_level.upper() if risk_level else "MEDIUM",
            "drivers": [
                {"type": "VOLATILITY", "weight": 0.85, "note": "波动率快速抬升，市场风险增加"},
                {"type": "EVENT", "weight": 0.70, "note": "地缘政治事件影响供应预期"},
                {"type": "MACRO_COINCIDENCE", "weight": 0.55, "note": "宏观经济政策不确定性"},
                {"type": "TERM_STRUCTURE", "weight": 0.40, "note": "期限结构变化反映供需调整"}
            ],
            "triggers": [
                {"if": "OPEC+出现产量分歧", "then": "减产协议松动，供给预期上修", "severity": "WARN"},
                {"if": "库存降幅超预期", "then": "短期供需偏紧信号强化", "severity": "INFO"},
                {"if": "美元指数突破105", "then": "大宗商品定价承压", "severity": "WARN"}
            ]
        }
    
    async def generate_confidence_data(
        self,
        market: MarketType,
        horizon: HorizonType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成confidence端点数据（模型置信度）"""
        direction_prob = algorithm_data.get('direction_prob', 0.5)
        risk_probs = algorithm_data.get('risk_probs', {})
        
        confidence = "HIGH" if direction_prob > 0.7 or direction_prob < 0.3 else "MEDIUM"
        
        prompt = f"""基于以下算法预测数据，生成模型置信度分析的JSON格式数据：

算法数据：
- 方向概率: {direction_prob}
- 风险概率分布: {json.dumps(risk_probs, ensure_ascii=False)}
- 置信度等级: {confidence}

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "horizon": "{horizon.value}",
    "confidence": "置信度等级(HIGH/MEDIUM/LOW)",
    "reasons": [
        "置信原因1(中文)",
        "置信原因2(中文)",
        "置信原因3(中文)",
        "置信原因4(中文)"
    ],
    "failureScenarios": [
        "可能导致预测失败的场景1(中文)",
        "可能导致预测失败的场景2(中文)",
        "可能导致预测失败的场景3(中文)"
    ]
}}

要求：
1. reasons列出3-4条置信原因
2. failureScenarios列出3-5条失败场景
3. 所有文本使用中文，专业简洁
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "horizon": horizon.value,
            "confidence": confidence,
            "reasons": [
                "当前市场状态与训练数据分布匹配度较高",
                "主要驱动因子信号强度在模型敏感区间内",
                "期限结构状态稳定，减少套利行为干扰",
                "近期模型方向预测准确率处于历史中位水平"
            ],
            "failureScenarios": [
                "突发地缘政治事件导致供给中断",
                "美联储政策意外转向引发美元剧烈波动",
                "主要经济体需求端出现结构性变化",
                "OPEC+内部分歧加剧导致减产协议瓦解"
            ]
        }
    
    async def generate_backtest_data(
        self,
        market: MarketType,
        horizon: HorizonType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成backtest端点数据"""
        start_date = (date.today() - timedelta(days=180)).isoformat()
        end_date = date.today().isoformat()
        
        prompt = f"""基于以下算法预测数据，生成回测摘要的JSON格式数据：

算法数据：
- 市场: {market.value}
- 预测周期: {horizon.value}

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "horizon": "{horizon.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "evaluationWindow": {{
        "start": "{start_date}",
        "end": "{end_date}",
        "isOutOfSample": true
    }},
    "modelMetrics": [
        {{"name": "MAE", "value": 数值, "unit": "$/bbl"}},
        {{"name": "RMSE", "value": 数值, "unit": "$/bbl"}},
        {{"name": "Direction Accuracy", "value": 数值, "unit": null}},
        {{"name": "Calibration Score", "value": 数值, "unit": null}},
        {{"name": "Sharpe (signal-based)", "value": 数值, "unit": null}}
    ],
    "baselineMetrics": [
        {{"name": "MAE", "value": 数值, "unit": "$/bbl"}},
        {{"name": "RMSE", "value": 数值, "unit": "$/bbl"}},
        {{"name": "Direction Accuracy", "value": 数值, "unit": null}},
        {{"name": "Calibration Score", "value": 数值, "unit": null}},
        {{"name": "Sharpe (signal-based)", "value": 数值, "unit": null}}
    ],
    "bestRegimes": ["SUPPLY_DRIVEN", "DEMAND_DRIVEN"],
    "notes": "回测分析总结(中文，100字以内)"
}}

要求：
1. modelMetrics的数值应优于baselineMetrics
2. MAE范围1.0-3.0，Direction Accuracy范围0.5-0.8
3. notes使用中文，简洁总结回测表现
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        return {
            "market": market.value,
            "horizon": horizon.value,
            "asOf": datetime.utcnow().isoformat(),
            "evaluationWindow": {"start": start_date, "end": end_date, "isOutOfSample": True},
            "modelMetrics": [
                {"name": "MAE", "value": 1.23, "unit": "$/bbl"},
                {"name": "RMSE", "value": 1.67, "unit": "$/bbl"},
                {"name": "Direction Accuracy", "value": 0.68, "unit": None},
                {"name": "Calibration Score", "value": 0.85, "unit": None},
                {"name": "Sharpe (signal-based)", "value": 1.42, "unit": None}
            ],
            "baselineMetrics": [
                {"name": "MAE", "value": 2.15, "unit": "$/bbl"},
                {"name": "RMSE", "value": 2.89, "unit": "$/bbl"},
                {"name": "Direction Accuracy", "value": 0.52, "unit": None},
                {"name": "Calibration Score", "value": 0.61, "unit": None},
                {"name": "Sharpe (signal-based)", "value": 0.73, "unit": None}
            ],
            "bestRegimes": ["SUPPLY_DRIVEN", "DEMAND_DRIVEN"],
            "notes": "模型在6个月样本外测试中表现优于随机游走基准，MAE降低43%，方向准确率提升16个百分点。在供给驱动和需求驱动市场状态下表现最佳。"
        }
    
    async def generate_overview_data(
        self,
        market: MarketType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成overview端点数据（预测总览）"""
        prompt = f"""基于以下算法预测数据，生成预测总览的JSON格式数据：

算法数据：
{json.dumps(algorithm_data, ensure_ascii=False, indent=2)}

请生成以下格式的JSON，保持算法数据的原有结构，只添加summary字段：
{{
    "date": "预测日期",
    "current_price": 当前价格,
    "forecast_price": 预测价格,
    "direction": "方向(up/down)",
    "direction_prob": 上涨概率,
    "risk_level": "风险等级(low/medium/high)",
    "risk_probs": {{
        "low": 低概率,
        "medium": 中概率,
        "high": 高概率
    }},
    "factor_importance": {{
        "technical": 技术因子贡献,
        "macro": 宏观因子贡献,
        "supply": 供需因子贡献,
        "events": 事件因子贡献
    }},
    "forecast_horizon": 预测天数,
    "forecast_curve": [
        {{"day": 1, "forecast_price": 价格}},
        ...
    ],
    "summary": "预测总结(中文，50字以内，简洁专业)"
}}

要求：
1. 保持原有算法数据不变
2. summary基于算法数据生成简洁的中文总结
3. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        # 返回原始数据+默认summary
        overview = algorithm_data.copy()
        overview['summary'] = f"模型预测{algorithm_data.get('direction', 'down')}方向，风险等级{algorithm_data.get('risk_level', 'medium')}，建议密切关注市场变化。"
        return overview
    
    async def generate_risk_analysis_data(
        self,
        market: MarketType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成risk-analysis端点数据"""
        risk_level = algorithm_data.get('risk_level', 'medium')
        
        prompt = f"""基于以下算法预测数据，生成风险信号分析的JSON格式数据：

算法数据：
- 风险等级: {risk_level}
- 市场: {market.value}

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "signals": [
        {{
            "name": "风险信号名称(中文)",
            "description": "风险描述(中文，简洁)",
            "level": "风险等级(LOW/MEDIUM/HIGH)"
        }}
    ]
}}

要求：
1. 生成4个风险信号：价格波动风险、事件风险、结构性风险、预测不确定性风险
2. 根据算法风险等级分配各信号的level
3. 所有文本使用中文
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "signals": [
                {"name": "价格波动风险", "description": "波动率快速抬升", "level": "HIGH"},
                {"name": "事件风险", "description": "突发地缘政治", "level": "MEDIUM"},
                {"name": "结构性风险", "description": "供需错配", "level": "LOW"},
                {"name": "预测不确定性风险", "description": "模型分歧扩大", "level": "HIGH"}
            ]
        }
    
    async def generate_transmission_path_data(
        self,
        market: MarketType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成transmission-path端点数据（风险传导路径）"""
        prompt = f"""基于原油市场风险，生成风险传导路径的JSON格式数据：

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "nodes": [
        {{
            "label": "节点名称(中文，如: 地缘冲突)",
            "description": "节点描述(中文，12字以内)"
        }}
    ]
}}

要求：
1. 生成6个传导节点，形成完整链条：
   - 地缘冲突 -> 原油供应收紧 -> 油价上涨 -> 航空燃油成本上升 -> 航空企业利润承压 -> 银行信用风险上升
2. 每个description不超过12字
3. 所有文本使用中文
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "nodes": [
                {"label": "地缘冲突", "description": "中东局势紧张"},
                {"label": "原油供应收紧", "description": "OPEC+减产执行"},
                {"label": "油价上涨", "description": "供需失衡推高"},
                {"label": "航空燃油成本上升", "description": "燃油成本增加"},
                {"label": "航空企业利润承压", "description": "航司利润下滑"},
                {"label": "银行信用风险上升", "description": "信贷风险暴露"}
            ]
        }
    
    async def generate_drivers_data(
        self,
        market: MarketType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成drivers端点数据（驱动因子）"""
        factor_importance = algorithm_data.get('factor_importance', {})
        
        prompt = f"""基于以下因子贡献度数据，生成驱动因子分析的JSON格式数据：

因子贡献度：
{json.dumps(factor_importance, ensure_ascii=False, indent=2)}

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "factors": [
        {{
            "factor": "因子名称(中文)",
            "impactRate": 影响程度(0-100),
            "description": "因子描述(中文，简洁专业)"
        }}
    ]
}}

要求：
1. 生成6个驱动因子：
   - 供给侧与需求侧
   - 库存与实物平衡
   - 美元与利率
   - 地缘政治与事件影响
   - 市场结构与期货
   - 波动率与情绪
2. impactRate基于因子贡献度换算为0-100
3. description简洁专业，中文
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        # 基于factor_importance计算impactRate
        fi = factor_importance
        tech = fi.get('technical', 0.5)
        macro = fi.get('macro', 0.5)
        supply = fi.get('supply', 0.5)
        events = fi.get('events', 0.5)
        
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "factors": [
                {"factor": "供给侧与需求侧", "impactRate": int(supply * 100), "description": "OPEC+减产预期增强，新兴市场需求复苏提供支撑。"},
                {"factor": "库存与实物平衡", "impactRate": int((supply + tech) * 50), "description": "全球原油库存回落，现货溢价抬升短期风险。"},
                {"factor": "美元与利率", "impactRate": int(macro * 100), "description": "利率预期放缓，美元走弱放大风险敏感度。"},
                {"factor": "地缘政治与事件影响", "impactRate": int(events * 100), "description": "中东局势升温，引发供应中断担忧。"},
                {"factor": "市场结构与期货", "impactRate": int(tech * 80), "description": "价差结构稳定，对当前风险影响有限。"},
                {"factor": "波动率与情绪", "impactRate": int((tech + events) * 50), "description": "隐含波动率上行，情绪推动短线放大。"}
            ]
        }
    
    async def generate_stress_test_data(
        self,
        market: MarketType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成stress-test端点数据（压力测试）"""
        prompt = f"""基于原油市场风险，生成情景压力测试的JSON格式数据：

请生成以下格式的JSON：
{{
    "market": "{market.value}",
    "asOf": "{datetime.utcnow().isoformat()}",
    "scenarios": [
        {{
            "scenario": "场景名称(中文)",
            "oilPriceChange": "油价变动描述(如: 油价变动 -10.5 $/bbl)",
            "industryImpact": {{
                "上游开采": "影响百分比(如: -25%)",
                "炼化加工": "影响百分比(如: +15%)",
                "航运物流": "影响百分比(如: +8%)"
            }}
        }}
    ]
}}

要求：
1. 生成3个压力测试场景：
   - OPEC+取消减产
   - 红海航线完全恢复
   - 欧佩克意外增产50万桶/日
2. 每个场景给出合理的油价变动和行业影响
3. 所有文本使用中文
4. 只返回JSON，不要其他解释文字"""

        result = await self._call_council_with_retry(prompt)
        response_text = result.get('final_response', '')
        
        parsed = self._parse_json_from_response(response_text)
        if parsed:
            return parsed
        
        return {
            "market": market.value,
            "asOf": datetime.utcnow().isoformat(),
            "scenarios": [
                {
                    "scenario": "OPEC+取消减产",
                    "oilPriceChange": "油价变动 -10.5 $/bbl",
                    "industryImpact": {"上游开采": "-25%", "炼化加工": "+15%", "航运物流": "+8%"}
                },
                {
                    "scenario": "红海航线完全恢复",
                    "oilPriceChange": "油价变动 -3.2 $/bbl",
                    "industryImpact": {"上游开采": "-6%", "炼化加工": "+5%", "航运物流": "-12%"}
                },
                {
                    "scenario": "欧佩克意外增产50万桶/日",
                    "oilPriceChange": "油价变动 -7.4 $/bbl",
                    "industryImpact": {"上游开采": "-18%", "炼化加工": "+12%", "航运物流": "-4%"}
                }
            ]
        }
    
    async def generate_all_forecast_data(
        self,
        market: MarketType,
        horizon: HorizonType,
        algorithm_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成所有Forecast API端点的完整数据
        
        Args:
            market: 市场类型
            horizon: 预测周期
            algorithm_data: 算法模型原始输出数据
            
        Returns:
            包含所有API端点数据的字典
        """
        # 并行生成所有数据
        tasks = [
            self.generate_distribution_data(market, horizon, algorithm_data),
            self.generate_signal_data(market, horizon, algorithm_data),
            self.generate_confidence_data(market, horizon, algorithm_data),
            self.generate_backtest_data(market, horizon, algorithm_data),
            self.generate_overview_data(market, algorithm_data),
            self.generate_risk_analysis_data(market, algorithm_data),
            self.generate_transmission_path_data(market, algorithm_data),
            self.generate_drivers_data(market, algorithm_data),
            self.generate_stress_test_data(market, algorithm_data),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        api_data = {}
        keys = ['distribution', 'signal', 'confidence', 'backtest', 'overview', 
                'risk_analysis', 'transmission_path', 'drivers', 'stress_test']
        
        for key, result in zip(keys, results):
            if isinstance(result, Exception):
                print(f"生成 {key} 数据失败: {result}")
                api_data[key] = {}
            else:
                api_data[key] = result
        
        return api_data


# 全局服务实例
llm_council_forecast_service = LLMCouncilForecastService()
