from typing import List, Dict, Any, Tuple
import re
from app.services.llm_council.client import query_models_parallel, query_model
from app.services.llm_council.config import llm_config

def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.
    """
    if not ranking_text:
        return []

    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [match.split('. ')[1].strip() for match in numbered_matches]
    
    return []

async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.
    """
    messages = [{"role": "user", "content": user_query}]

    responses = await query_models_parallel(llm_config.COUNCIL_MODELS, messages)
    stage1_results = []
    for model, response in responses.items():
        if response is not None: 
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.
    """
    if not stage1_results:
        return [], {}

    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    responses = await query_models_parallel(llm_config.COUNCIL_MODELS, messages)


    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking_response": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> str:
    """
    Stage 3: The Chairman model synthesizes the final answer.
    """
    if not stage1_results:
        return "Failed to get any responses from the council."

    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking_response']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""

    messages = [{"role": "user", "content": chairman_prompt}]
    
    response = await query_model(llm_config.CHAIRMAN_MODEL, messages)
    
    if response and response.get('content'):
        return response['content']
    else:
        return "The Chairman failed to synthesize a response."

async def run_full_council(user_query: str) -> Dict[str, Any]:
    """
    Run the full 3-stage council process.
    """
    # Stage 1
    stage1_results = await stage1_collect_responses(user_query)
    
    if not stage1_results:
        return {
            "error": "No models returned a response in Stage 1",
            "final_response": "The council failed to convene (no responses)."
        }

    # Stage 2
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Stage 3
    final_response = await stage3_synthesize_final(
        user_query, 
        stage1_results, 
        stage2_results
    )

    return {
        "final_response": final_response,
        "details": {
            "stage1_results": stage1_results,
            "stage2_results": stage2_results,
            "label_to_model": label_to_model
        }
    }
