<<<<<<< HEAD
"""
测试豆包大模型API调用
"""
import asyncio
import httpx
import json

# 配置
API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
API_KEY = "9169354a-7e2c-4578-b387-936a97ca1ff9"
MODEL = "doubao-seed-1-8-251228"


async def test_doubao_api():
    """测试豆包API基本调用"""
    print("=" * 50)
    print("测试豆包大模型API")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 测试prompt - 生成风险分析
    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "你是一位专业的原油市场分析师，擅长风险分析和市场解读。请用简洁专业的语言回答问题。"
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "请用一句话（不超过50字）分析当前WTI原油市场的波动率风险。当前20日历史波动率已突破25%阈值。"
                    }
                ]
            }
        ]
    }
    
    print(f"\n📤 请求模型: {MODEL}")
    print(f"📤 Prompt: 分析WTI原油市场波动率风险")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            
            print(f"📥 HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n📥 原始响应:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                
                # 解析响应 - output是列表
                output = data.get("output", [])
                
                result = None
                if isinstance(output, list):
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            if isinstance(content, list):
                                texts = [c.get("text", "") for c in content if c.get("type") == "output_text"]
                                result = "".join(texts)
                            break
                
                if result:
                    print(f"\n✅ 解析后的回复:")
                    print(f"   {result}")
                else:
                    print("⚠️ 无法解析响应")
            else:
                print(f"❌ 请求失败:")
                print(response.text)
                
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print("\n" + "=" * 50)


async def test_forecast_summary():
    """测试预测总结生成"""
    print("\n测试预测总结生成")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "你是一位专业的原油市场分析师。请用简洁专业的语言（不超过80字）总结市场预测。"
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """请总结以下原油市场预测：
- 当前价格: $74.6/桶
- 预测价格: $75.8/桶
- 预测方向: 上涨
- 风险等级: 高
- 关键因素: OPEC+政策、库存变化、地缘风险

请给出简短的市场预测总结："""
                    }
                ]
            }
        ]
    }
    
    print(f"📤 测试: 生成预测总结")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", [])
                
                result = None
                if isinstance(output, list):
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            if isinstance(content, list):
                                texts = [c.get("text", "") for c in content if c.get("type") == "output_text"]
                                result = "".join(texts)
                            break
                
                if result:
                    print(f"✅ 预测总结:")
                    print(f"   {result}")
                else:
                    print("⚠️ 无法解析响应")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"❌ 错误: {e}")


async def main():
    await test_doubao_api()
    await test_forecast_summary()
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
=======
"""
测试豆包大模型API调用
"""
import asyncio
import httpx
import json

# 配置
API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
API_KEY = "9169354a-7e2c-4578-b387-936a97ca1ff9"
MODEL = "doubao-seed-1-8-251228"


async def test_doubao_api():
    """测试豆包API基本调用"""
    print("=" * 50)
    print("测试豆包大模型API")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 测试prompt - 生成风险分析
    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "你是一位专业的原油市场分析师，擅长风险分析和市场解读。请用简洁专业的语言回答问题。"
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "请用一句话（不超过50字）分析当前WTI原油市场的波动率风险。当前20日历史波动率已突破25%阈值。"
                    }
                ]
            }
        ]
    }
    
    print(f"\n📤 请求模型: {MODEL}")
    print(f"📤 Prompt: 分析WTI原油市场波动率风险")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            
            print(f"📥 HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n📥 原始响应:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
                
                # 解析响应 - output是列表
                output = data.get("output", [])
                
                result = None
                if isinstance(output, list):
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            if isinstance(content, list):
                                texts = [c.get("text", "") for c in content if c.get("type") == "output_text"]
                                result = "".join(texts)
                            break
                
                if result:
                    print(f"\n✅ 解析后的回复:")
                    print(f"   {result}")
                else:
                    print("⚠️ 无法解析响应")
            else:
                print(f"❌ 请求失败:")
                print(response.text)
                
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    print("\n" + "=" * 50)


async def test_forecast_summary():
    """测试预测总结生成"""
    print("\n测试预测总结生成")
    print("=" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": MODEL,
        "input": [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": "你是一位专业的原油市场分析师。请用简洁专业的语言（不超过80字）总结市场预测。"
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": """请总结以下原油市场预测：
- 当前价格: $74.6/桶
- 预测价格: $75.8/桶
- 预测方向: 上涨
- 风险等级: 高
- 关键因素: OPEC+政策、库存变化、地缘风险

请给出简短的市场预测总结："""
                    }
                ]
            }
        ]
    }
    
    print(f"📤 测试: 生成预测总结")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", [])
                
                result = None
                if isinstance(output, list):
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            if isinstance(content, list):
                                texts = [c.get("text", "") for c in content if c.get("type") == "output_text"]
                                result = "".join(texts)
                            break
                
                if result:
                    print(f"✅ 预测总结:")
                    print(f"   {result}")
                else:
                    print("⚠️ 无法解析响应")
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"❌ 错误: {e}")


async def main():
    await test_doubao_api()
    await test_forecast_summary()
    print("\n🎉 测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
>>>>>>> 83767a8 (chore_initial_import)
