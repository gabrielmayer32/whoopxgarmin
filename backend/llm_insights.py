from typing import Dict, List, Optional
import logging
import json
import hashlib
import os
import threading
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / ".llm_cache"
DAILY_CACHE = CACHE_DIR / "daily.json"
MODEL_PATH = Path(__file__).parent.parent / "models" / "phi-3-mini-q4.gguf"

_openai_client = None
_phi_model = None
_phi_load_lock = threading.Lock()
_phi_semaphore = threading.Semaphore(1)


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_phi():
    global _phi_model
    if _phi_model is None:
        with _phi_load_lock:
            if _phi_model is None:
                from llama_cpp import Llama
                logger.info("Loading Phi-3-mini fallback model...")
                _phi_model = Llama(model_path=str(MODEL_PATH), n_ctx=2048, n_gpu_layers=0, verbose=False)
                logger.info("Phi-3-mini loaded.")
    return _phi_model


def _sections_hash(sections: dict) -> str:
    payload = {
        name: {"f": d["facts"], "m": {k: v for k, v in d["metrics"].items() if v is not None}}
        for name, d in sections.items()
        if d.get("facts")
    }
    return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _load_daily_cache() -> dict:
    if DAILY_CACHE.exists():
        try:
            return json.loads(DAILY_CACHE.read_text())
        except Exception:
            pass
    return {}


def _save_daily_cache(data: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    DAILY_CACHE.write_text(json.dumps(data))


def invalidate_insights_cache():
    """Call this when a new activity is added so insights regenerate on next request."""
    cache = _load_daily_cache()
    cache.pop("date", None)
    cache.pop("hash", None)
    cache.pop("coaching", None)
    _save_daily_cache(cache)


def generate_all_coaching(sections: Dict[str, dict]) -> Dict[str, str]:
    """
    sections: { section_name: { "facts": [...], "metrics": {...} }, ... }
    Returns: { section_name: "coaching text", ... }
    Regenerates at most once per day, or when invalidate_insights_cache() is called.
    """
    today = date.today().isoformat()
    content_hash = _sections_hash(sections)
    cache = _load_daily_cache()

    if cache.get("date") == today and cache.get("hash") == content_hash and cache.get("coaching"):
        logger.info("Returning cached insights for today")
        return cache["coaching"]

    active = {name: data for name, data in sections.items() if data.get("facts")}
    if not active:
        return {name: "" for name in sections}

    section_blocks = []
    for name, data in active.items():
        facts_text = "\n".join(f"  - {f}" for f in data["facts"])
        metrics_lines = [f"    {k}: {v}" for k, v in data["metrics"].items() if v is not None]
        metrics_text = "\n".join(metrics_lines) or "    (no data)"
        section_blocks.append(f"[{name.upper()}]\nMetrics:\n{metrics_text}\nObservations:\n{facts_text}")

    sections_text = "\n\n".join(section_blocks)
    keys = list(active.keys())

    # ── Try OpenAI first ──────────────────────────────────────────────────────
    if os.environ.get("OPENAI_API_KEY"):
        try:
            client = _get_openai()
            prompt = (
                "You are an elite sports performance coach. A client has shared their health and training data.\n\n"
                "For each category below, write exactly 2-3 sentences of personalized, actionable coaching advice. "
                "Be direct and specific. Do not repeat the numbers — interpret them.\n\n"
                f"{sections_text}\n\n"
                f"Respond with only a JSON object with these keys: {keys}"
            )
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            result = json.loads(response.choices[0].message.content.strip())
            out = {name: result.get(name, "") for name in sections}
            _save_daily_cache({"date": today, "hash": content_hash, "coaching": out})
            return out
        except Exception as e:
            logger.warning(f"OpenAI inference failed, falling back to Phi-3: {e}")

    # ── Fallback: local Phi-3-mini ────────────────────────────────────────────
    if not MODEL_PATH.exists():
        logger.warning("Phi-3-mini model file not found, no coaching available")
        return {name: "" for name in sections}

    try:
        phi = _get_phi()
    except Exception as e:
        logger.warning(f"Could not load Phi-3-mini: {e}")
        return {name: "" for name in sections}

    out = {}
    for name, data in sections.items():
        if not data.get("facts"):
            out[name] = ""
            continue
        facts_text = "\n".join(f"- {f}" for f in data["facts"])
        metrics_lines = [f"  {k}: {v}" for k, v in data["metrics"].items() if v is not None]
        user_message = (
            "You are an elite sports performance coach. A client has shared their health and training data.\n\n"
            f"TODAY'S KEY METRICS:\n{chr(10).join(metrics_lines) or '  (no data)'}\n\n"
            f"DATA-DRIVEN OBSERVATIONS:\n{facts_text}\n\n"
            "Write 2-3 sentences of personalized, actionable coaching advice. "
            "Be direct and specific. Do not repeat the numbers — interpret them."
        )
        try:
            with _phi_semaphore:
                response = phi.create_chat_completion(
                    messages=[{"role": "user", "content": user_message}],
                    max_tokens=120,
                    temperature=0.7,
                    top_p=0.9,
                )
            out[name] = response["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"Phi-3 inference failed for {name}: {e}")
            out[name] = ""

    _save_daily_cache({"date": today, "hash": content_hash, "coaching": out})
    return out
