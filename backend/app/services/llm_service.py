import json
import logging
import os
import threading
import datetime
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings
from app.models.bill import BillData, BillItem
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_token_lock = threading.Lock()
_token_file = os.path.join(settings.BASE_DIR, "data", "token_usage.json")


def _record_token_usage(prompt_tokens: int, completion_tokens: int):
    """Record LLM token consumption to a JSON file, keyed by ISO hour."""
    now = datetime.datetime.now(datetime.timezone.utc)
    hour_key = now.strftime("%Y-%m-%dT%H:00Z")
    with _token_lock:
        data = {}
        if os.path.exists(_token_file):
            try:
                with open(_token_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        entry = data.get(hour_key, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "llm_calls": 0})
        entry["prompt_tokens"] += prompt_tokens
        entry["completion_tokens"] += completion_tokens
        entry["total_tokens"] += prompt_tokens + completion_tokens
        entry["llm_calls"] += 1
        data[hour_key] = entry
        os.makedirs(os.path.dirname(_token_file), exist_ok=True)
        with open(_token_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_API_BASE
        self.model = settings.LLM_MODEL_NAME
        
        # Set default base URL for known providers if not set
        if not self.base_url:
            if self.provider == "deepseek":
                self.base_url = "https://api.deepseek.com"
            elif self.provider == "tongyi":
                self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
            elif self.provider == "wenxin":
                self.base_url = "https://qianfan.baidubce.com/v2"
            elif self.provider == "vllm":
                self.base_url = "http://localhost:8000/v1"

    def update_config(self, provider: str, model_name: str, api_key: str = None, api_base: str = None):
        """
        Dynamically update LLM configuration.
        """
        self.provider = provider
        self.model = model_name
        if api_key:
            self.api_key = api_key
        if api_base:
            self.base_url = api_base
        logger.info(f"LLM configuration updated: provider={provider}, model={model_name}")

    def get_config(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "api_base": self.base_url
        }

    async def refine_extraction(self, ocr_text: str, initial_data: BillData) -> BillData:
        """
        Use LLM to refine OCR extraction and format data according to business rules.
        """
        prompt = self._construct_prompt(ocr_text, initial_data)
        
        for attempt in range(3):
            try:
                response = await self._call_llm(prompt)
                refined_data = self._parse_response(response)
                
                # Merge with initial data (LLM usually better at structure, OCR better at raw values)
                final_data = self._merge_data(initial_data, refined_data)
                
                # Validate
                if self._validate_data(final_data):
                    return final_data
                else:
                    logger.warning(f"Validation failed for LLM response (attempt {attempt+1})")
            except Exception as e:
                logger.error(f"LLM call failed (attempt {attempt+1}): {e}")
        
        # Fallback to rule-based data if LLM fails
        logger.error("LLM extraction failed after retries. Returning rule-based data.")
        initial_data.review_flag = True
        return initial_data

    def _construct_prompt(self, text: str, data: BillData) -> str:
        return f"""
        You are an intelligent electricity bill analysis assistant. 
        Your task is to extract structured data from the following OCR text of an electricity bill.
        
        OCR Text:
        {text}
        
        Please extract the following fields and return ONLY a JSON object:
        - user_id (户号)
        - user_name (户名)
        - address (地址)
        - billing_period (计费周期/月份)
        - total_usage (总电量 kWh)
        - total_cost (总金额 元)
        - items: List of tariff items, each containing:
          - period (e.g. 尖时, 峰段, 平段, 谷段)
          - electricity_usage (电量)
          - price (电价)
          - cost (金额)
          
        Refine the data based on these preliminary extracted values (use if correct, correct if wrong):
        {data.model_dump_json(exclude_none=True)}
        
        Output format must be strictly JSON. No markdown code blocks.
        """

    async def _call_llm(self, prompt: str) -> str:
        if not self.api_key:
            logger.error("No LLM API Key configured. Extraction will return empty results. Set LLM_API_KEY in .env to enable LLM extraction.")
            return "{}"
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that extracts data from documents to JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }
        
        try:
            # Increase timeout to 120s for complex extraction tasks
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Ensure base_url does not end with slash
                base = self.base_url.rstrip('/') if self.base_url else "https://api.deepseek.com"

                # Detect Anthropic-compatible endpoint misconfiguration
                if "/anthropic" in base:
                    logger.warning(
                        f"Base URL '{base}' appears to be an Anthropic-compatible endpoint. "
                        "This service uses OpenAI-format requests. Stripping /anthropic suffix."
                    )
                    base = base.replace("/anthropic", "")

                # Check if base_url already contains /chat/completions (user misconfiguration handling)
                if base.endswith("/chat/completions"):
                    url = base
                else:
                    url = f"{base}/chat/completions"

                logger.info(f"Calling LLM at {url} with model {self.model}...")
                resp = await client.post(url, json=payload, headers=headers)
                logger.info(f"LLM response status: {resp.status_code}")

                if resp.status_code >= 400:
                    error_body = resp.text[:500]
                    logger.error(f"LLM HTTP {resp.status_code}: {error_body}")

                resp.raise_for_status()
                response_json = resp.json()
                
                # Record token usage
                usage = response_json.get("usage", {})
                if usage:
                    _record_token_usage(
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0)
                    )
                
                return response_json["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text[:300]}")
            return json.dumps({})
        except Exception as e:
            logger.error(f"LLM call failed: {str(e) or repr(e)}")
            # Fallback to mock/empty on error to not crash the flow
            return json.dumps({})

    def _parse_response(self, response_text: str) -> BillData:
        try:
            # Cleanup markdown if present
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            data_dict = json.loads(clean_text)
            return BillData(**data_dict)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise

    def _merge_data(self, rule_data: BillData, llm_data: BillData) -> BillData:
        # Strategy: Trust LLM for structure/labels, trust Rule for specific numbers if confident?
        # For simplicity, we trust LLM but fallback to Rule if LLM is missing fields
        merged = llm_data.model_copy()
        
        if not merged.user_id and rule_data.user_id:
            merged.user_id = rule_data.user_id
            
        if not merged.total_cost and rule_data.total_cost:
            merged.total_cost = rule_data.total_cost
            
        return merged

    def _validate_data(self, data: BillData) -> bool:
        # Basic validation
        if not data.user_id or not data.total_cost:
            return False
        return True

    async def answer_with_rag(self, query: str, context_chunks: list[Dict]) -> str:
        """
        Generate answer using RAG context.
        """
        prompt = self._construct_rag_prompt(query, context_chunks)
        try:
            # Use a more generic chat call
            response = await self._call_chat_llm(prompt, system_prompt="You are a helpful assistant. Answer based on the provided context.")
            return response
        except Exception as e:
            logger.error(f"RAG generation failed: {e}")
            raise

    def _construct_rag_prompt(self, query: str, context_chunks: list[Dict]) -> str:
        context_text = ""
        for i, chunk in enumerate(context_chunks):
            source = chunk.get("metadata", {}).get("source", "Unknown")
            context_text += f"[{i+1}] (Source: {source})\n{chunk['text']}\n\n"
            
        return f"""
        Use the following context to answer the user's question.
        If the answer is not in the context, say "I don't know based on the provided documents."
        Cite the source using [1], [2] notation.
        
        Context:
        {context_text}
        
        Question: 
        {query}
        
        Answer:
        """

    async def _call_chat_llm(self, prompt: str, system_prompt: str = "You are a helpful assistant.") -> str:
        if not self.api_key:
             return "Mock Answer (No API Key)"
             
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Ensure base_url does not end with slash
            base = self.base_url.rstrip('/') if self.base_url else "https://api.deepseek.com"

            # Detect Anthropic-compatible endpoint misconfiguration
            if "/anthropic" in base:
                logger.warning(
                    f"Base URL '{base}' appears to be an Anthropic-compatible endpoint. "
                    "This service uses OpenAI-format requests. Stripping /anthropic suffix."
                )
                base = base.replace("/anthropic", "")

            if base.endswith("/chat/completions"):
                url = base
            else:
                url = f"{base}/chat/completions"

            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            response_json = resp.json()
            
            # Record token usage
            usage = response_json.get("usage", {})
            if usage:
                _record_token_usage(
                    usage.get("prompt_tokens", 0),
                    usage.get("completion_tokens", 0)
                )
            
            return response_json["choices"][0]["message"]["content"]

llm_service = LLMService()
