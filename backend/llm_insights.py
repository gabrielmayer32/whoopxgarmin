from pathlib import Path
from typing import List, Optional
import logging
import json
import hashlib
import threading

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent.parent / "models" / "phi-3-mini-q4.gguf"
CACHE_DIR = Path(__file__).parent.parent / ".llm_cache"

_llm = None
_llm_load_lock = threading.Lock()
_inference_semaphore = threading.Semaphore(1)


def _get_llm():
    global _llm
    if _llm is None:
        with _llm_load_lock:
            if _llm is None:
                from llama_cpp import Llama
                logger.info("Loading Phi-3-mini model...")
                _llm = Llama(
                    model_path=str(MODEL_PATH),
                    n_ctx=2048,
                    n_gpu_layers=0,
                    verbose=False,
                )
                logger.info("Model loaded.")
    return _llm


def _cache_key(facts: List[str], metrics: dict) -> str:
    payload = json.dumps({"f": facts, "m": {k: v for k, v in metrics.items() if v is not None}}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    path = CACHE_DIR / f"{key}.txt"
    return path.read_text() if path.exists() else None


def _cache_set(key: str, value: str):
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{key}.txt").write_text(value)


def generate_llm_insights(facts: List[str], metrics: dict) -> str:
    if not MODEL_PATH.exists():
        return ""

    key = _cache_key(facts, metrics)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    try:
        llm = _get_llm()
    except Exception as e:
        logger.warning(f"Could not load LLM: {e}")
        return ""

    facts_text = "\n".join(f"- {f}" for f in facts) if facts else "- No specific alerts today."
    metrics_lines = [f"  {k}: {v}" for k, v in metrics.items() if v is not None]
    metrics_text = "\n".join(metrics_lines) if metrics_lines else "  (no data)"

    user_message = (
        "You are an elite sports performance coach. A client has shared their health and training data.\n\n"
        f"TODAY'S KEY METRICS:\n{metrics_text}\n\n"
        f"DATA-DRIVEN OBSERVATIONS:\n{facts_text}\n\n"
        "Write 2-3 sentences of personalized, actionable coaching advice. "
        "Be direct and specific. Do not repeat the numbers — interpret them."
    )

    try:
        with _inference_semaphore:
            response = llm.create_chat_completion(
                messages=[{"role": "user", "content": user_message}],
                max_tokens=120,
                temperature=0.7,
                top_p=0.9,
            )
        text = response["choices"][0]["message"]["content"].strip()
        _cache_set(key, text)
        return text
    except Exception as e:
        logger.warning(f"LLM inference failed: {e}")
        return ""
