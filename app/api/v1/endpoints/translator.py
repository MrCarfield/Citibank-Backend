import json
from datetime import datetime
from typing import Any
from fastapi import APIRouter, HTTPException, Depends
from app.schemas.translator import TranslatorRequest, TranslatorResponse
from app.services.llm_council import get_council_response
from app.services.oil_risk_inference import get_oil_neural_features

router = APIRouter()

def construct_llm_prompt(request: TranslatorRequest, neural_data: dict) -> str:
    """
    构建 LLM Council 的提示词。
    """
    return f"""
You are an expert Oil & Gas Financial Analyst at Citibank.
Your task is to translate raw neural network predictions into a client-specific impact report.

### Input Context
- Client ID: {request.clientId}
- Market: {request.market.value}
- Horizon: {request.horizon.value}
- Analysis Date: {request.asOf or datetime.now()}

### Mock Neural Network Predictions (The "Truth")
- Predicted Price Change: {neural_data['predicted_price_change_pct']:.2%}
- Predicted Volatility Change: {neural_data['predicted_volatility_change_pct']:.2%}
- Model Confidence: {neural_data['confidence_score']:.2f}
- Primary Market Driver: {neural_data['primary_driver']}
- Secondary Market Driver: {neural_data['secondary_driver']}

### Instructions
1. **Generate Client Profile**: Invent a realistic client profile for "{request.clientId}" (e.g., if ID is 'Shell', make it a major Upstream/Downstream integrated player; if 'Airline', a consumer). If the ID is generic like 'ClientA', invent a plausible profile (e.g., a mid-size shale producer).
2. **Analyze Impact**: Based on the *Predicted Price Change* and *Client Profile*, determine the stress levels.
   - Example: A price DROP hurts Upstream producers (High Stress) but helps Airlines (Low Stress/Benefit).
   - Example: High Volatility hurts those with low financial buffers.
3. **Construct Narrative**: Create key drivers, transmission paths, and talk points that logically follow from the prediction.

### Response Format
You must return a **single valid JSON object** matching the following structure exactly. Do not include markdown formatting (like ```json).

{{
  "client": {{
    "clientId": "{request.clientId}",
    "name": "Generated Company Name",
    "type": "UPSTREAM" | "TRADER" | "DOWNSTREAM",
    "currency": "USD",
    "exposureDirection": "BENEFITS_FROM_UP" | "HURT_BY_UP" | "MIXED",
    "passThroughAbility": "STRONG" | "MEDIUM" | "WEAK",
    "financialBuffer": "HIGH" | "MEDIUM" | "LOW",
    "volatilitySensitivity": "HIGH" | "MEDIUM" | "LOW",
    "notes": "Brief description of client business model"
  }},
  "market": "{request.market.value}",
  "horizon": "{request.horizon.value}",
  "asOf": "{request.asOf or datetime.now().isoformat()}",
  "assumptions": ["Assumption 1", "Assumption 2"],
  "impactScore": {{
    "operatingStress": "LOW" | "MEDIUM" | "HIGH",
    "fundingStress": "LOW" | "MEDIUM" | "HIGH",
    "confidence": {neural_data['confidence_score']}
  }},
  "keyDrivers": [
    {{
      "factorId": "driver-1",
      "factorName": "{neural_data['primary_driver']}",
      "category": "SUPPLY" | "DEMAND" | "MACRO_FINANCIAL" | "FX" | "EVENTS" | "OTHER",
      "direction": "UP" | "DOWN" | "NEUTRAL" | "MIXED" | "UNCERTAIN",
      "strength": 0.9,
      "evidence": ["Evidence point A"]
    }}
  ],
  "transmissionPath": [
    {{
      "from": "Oil Price",
      "to": "Revenue",
      "note": "Direct impact description",
      "direction": "UP" | "DOWN" | "MIXED" | "UNCERTAIN"
    }}
  ],
  "rmTalkPoints": [
    "Talk point 1 based on analysis",
    "Talk point 2"
  ],
  "bankActionChecklist": [
    "Action item 1",
    "Action item 2"
  ]
}}
"""

@router.post("/run", response_model=TranslatorResponse)
async def run_translator(request: TranslatorRequest):
    """
    运行石油冲击转换器以生成特定于客户的影响、谈话要点和行动清单。
    """
    try:
        neural_data = await get_oil_neural_features(request)
        prompt = construct_llm_prompt(request, neural_data)
        llm_response_text = await get_council_response(prompt)
        clean_json = llm_response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        return TranslatorResponse(**data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 生成了无效的 JSON。请重试。")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
