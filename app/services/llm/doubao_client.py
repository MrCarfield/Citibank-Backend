"""
豆包大模型客户端 (火山引擎 Volcengine Ark)

API文档参考: https://www.volcengine.com/docs/82379/1263482
"""
import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings


class DoubaoClient:
    """豆包大模型API客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or settings.DOUBAO_API_KEY
        self.api_url = api_url or settings.DOUBAO_API_URL
        self.model = model or settings.DOUBAO_MODEL
    
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: float = 60.0,
    ) -> Optional[str]:
        """
        发送聊天请求
        
        Args:
            prompt: 用户输入的prompt
            system_prompt: 系统提示词(可选)
            timeout: 请求超时时间
            
        Returns:
            模型生成的文本，失败返回None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # 构建input消息列表
        messages: List[Dict[str, Any]] = []
        
        # 添加系统提示
        if system_prompt:
            messages.append({
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt
                    }
                ]
            })
        
        # 添加用户消息
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": prompt
                }
            ]
        })
        
        payload = {
            "model": self.model,
            "input": messages,
        }
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # 解析响应
                if "error" in data:
                    print(f"Doubao API Error: {data['error']}")
                    return None
                
                # 火山引擎Ark API响应格式
                # output是列表，包含reasoning和message两种类型
                output = data.get("output", [])
                
                if isinstance(output, list):
                    # 查找type为"message"的项
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            if isinstance(content, list):
                                texts = [
                                    c.get("text", "") 
                                    for c in content 
                                    if c.get("type") == "output_text"
                                ]
                                return "".join(texts) if texts else None
                            return content if content else None
                
                return None
                
        except httpx.TimeoutException:
            print(f"Doubao API request timeout after {timeout}s")
            return None
        except httpx.HTTPStatusError as e:
            print(f"Doubao API HTTP error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"Doubao API error: {e}")
            return None
    
    async def generate_risk_analysis(
        self,
        risk_type: str,
        market_context: str,
    ) -> str:
        """
        生成风险分析说明
        
        Args:
            risk_type: 风险类型 (如 "价格波动", "地缘政治" 等)
            market_context: 市场背景信息
            
        Returns:
            生成的风险分析文本
        """
        system_prompt = """你是一位专业的原油市场分析师，擅长风险分析和市场解读。
请用简洁专业的语言（不超过50字）描述风险影响，语言要具体、有数据支撑。"""
        
        prompt = f"""请分析以下风险因素对原油市场的影响：
风险类型: {risk_type}
市场背景: {market_context}

请给出简短精准的分析说明："""
        
        result = await self.chat(prompt, system_prompt)
        return result or f"{risk_type}风险需要持续关注"
    
    async def generate_forecast_summary(
        self,
        current_price: float,
        forecast_price: float,
        direction: str,
        risk_level: str,
        key_factors: List[str],
    ) -> str:
        """
        生成预测总结
        
        Args:
            current_price: 当前价格
            forecast_price: 预测价格
            direction: 预测方向
            risk_level: 风险等级
            key_factors: 关键因素列表
            
        Returns:
            生成的预测总结文本
        """
        system_prompt = """你是一位专业的原油市场分析师。
请用简洁专业的语言（不超过80字）总结市场预测，包含关键因素和风险提示。"""
        
        direction_cn = "上涨" if direction == "up" else "下跌"
        risk_cn = {"LOW": "低", "MEDIUM": "中等", "HIGH": "高"}.get(risk_level, "中等")
        
        prompt = f"""请总结以下原油市场预测：
- 当前价格: ${current_price}/桶
- 预测价格: ${forecast_price}/桶
- 预测方向: {direction_cn}
- 风险等级: {risk_cn}
- 关键因素: {', '.join(key_factors)}

请给出简短的市场预测总结："""
        
        result = await self.chat(prompt, system_prompt)
        return result or f"油价预计{direction_cn}，当前风险等级{risk_cn}。"
    
    async def generate_confidence_reasons(
        self,
        confidence_level: str,
        market_regime: str,
        model_performance: str,
    ) -> List[str]:
        """
        生成模型置信度原因
        
        Args:
            confidence_level: 置信度等级
            market_regime: 市场状态
            model_performance: 模型表现描述
            
        Returns:
            置信度原因列表
        """
        system_prompt = """你是一位量化分析师，负责解释预测模型的置信度。
请列出3-4条简洁的原因（每条不超过40字），用数字标号。"""
        
        confidence_cn = {"HIGH": "高", "MEDIUM": "中等", "LOW": "低"}.get(confidence_level, "中等")
        
        prompt = f"""请解释模型为何给出{confidence_cn}置信度：
- 市场状态: {market_regime}
- 模型表现: {model_performance}

请列出置信度原因："""
        
        result = await self.chat(prompt, system_prompt)
        
        if result:
            # 解析返回的列表
            lines = [line.strip() for line in result.split("\n") if line.strip()]
            reasons = []
            for line in lines:
                # 去除序号
                cleaned = line.lstrip("0123456789.-、) ").strip()
                if cleaned:
                    reasons.append(cleaned)
            if reasons:
                return reasons[:4]
        
        # 默认返回
        return [
            f"当前市场处于{market_regime}，与训练数据分布匹配",
            "近期模型预测准确率处于历史中位水平",
            "主要驱动因子的信号强度在模型敏感区间内",
        ]
    
    async def generate_failure_scenarios(
        self,
        market: str,
        current_drivers: List[str],
    ) -> List[str]:
        """
        生成可能导致预测失败的场景
        
        Args:
            market: 市场类型
            current_drivers: 当前主要驱动因素
            
        Returns:
            失败场景列表
        """
        system_prompt = """你是一位风险管理专家，擅长识别尾部风险。
请列出4-5个可能导致预测失效的场景（每条不超过50字），用数字标号。"""
        
        prompt = f"""针对{market}原油市场，当前主要驱动因素为：{', '.join(current_drivers)}

请列出可能导致模型预测失效的场景："""
        
        result = await self.chat(prompt, system_prompt)
        
        if result:
            lines = [line.strip() for line in result.split("\n") if line.strip()]
            scenarios = []
            for line in lines:
                cleaned = line.lstrip("0123456789.-、) ").strip()
                if cleaned:
                    scenarios.append(cleaned)
            if scenarios:
                return scenarios[:5]
        
        # 默认返回
        return [
            "突发地缘政治事件导致供给中断",
            "美联储政策意外转向引发美元剧烈波动",
            "中国经济刺激政策超预期",
            "OPEC+内部分歧导致减产协议瓦解",
        ]
    
    async def generate_backtest_notes(
        self,
        model_mae: float,
        baseline_mae: float,
        direction_accuracy: float,
        best_regimes: List[str],
    ) -> str:
        """
        生成回测分析说明
        
        Args:
            model_mae: 模型MAE
            baseline_mae: 基线MAE
            direction_accuracy: 方向准确率
            best_regimes: 最佳表现的市场状态
            
        Returns:
            回测分析说明文本
        """
        system_prompt = """你是一位量化策略分析师，负责撰写回测报告。
请用专业简洁的语言（80-120字）总结回测表现，包含关键指标和建议。"""
        
        improvement = ((baseline_mae - model_mae) / baseline_mae) * 100
        
        prompt = f"""请总结以下回测结果：
- 模型MAE: ${model_mae}/桶
- 基线MAE: ${baseline_mae}/桶 (相对改善{improvement:.1f}%)
- 方向准确率: {direction_accuracy*100:.1f}%
- 最佳表现状态: {', '.join(best_regimes)}

请给出回测分析总结："""
        
        result = await self.chat(prompt, system_prompt)
        return result or f"模型相对基准MAE降低{improvement:.1f}%，方向准确率{direction_accuracy*100:.1f}%。"
    
    async def generate_driver_description(
        self,
        factor_name: str,
        impact_rate: float,
        market_context: str,
    ) -> str:
        """
        生成驱动因子描述
        
        Args:
            factor_name: 因子名称
            impact_rate: 影响率
            market_context: 市场背景
            
        Returns:
            因子描述文本
        """
        system_prompt = """你是一位原油市场分析师。
请用一句话（不超过30字）描述该因子对油价的影响。"""
        
        prompt = f"""因子: {factor_name}
影响强度: {impact_rate}%
市场背景: {market_context}

请描述该因子的影响："""
        
        result = await self.chat(prompt, system_prompt)
        return result or f"{factor_name}因素影响显著。"


# 创建全局客户端实例
doubao_client = DoubaoClient()
