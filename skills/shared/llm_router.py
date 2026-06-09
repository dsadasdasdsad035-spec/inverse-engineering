"""LLM client router: all operations use MiniMax."""
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Auto-load .env from repo root
_env = Path(__file__).parent.parent.parent / ".env"
if _env.exists():
    for line in _env.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.chat/v1").rstrip("/")

# In-memory cache for LLM results (key: prompt hash)
_WRITE_CACHE: dict[str, str] = {}

MAX_PARALLEL_REQUESTS = int(os.environ.get("MAX_PARALLEL_LLM", 3))

# Default model for writing/translation
WRITE_MODEL = os.environ.get("MINIMAX_WRITE_MODEL", "abab6.5s-chat")
EVAL_MODEL = "abab6.5s-chat"


_DEFAULT_TIMEOUT = 60  # seconds


def _minimax_client():
    import httpx
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    base_url = os.environ.get("MINIMAX_BASE_URL", MINIMAX_BASE_URL).rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    class MinimaxClient:
        def complete(self, prompt: str, model: str = WRITE_MODEL) -> str:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            r = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=_DEFAULT_TIMEOUT,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    return MinimaxClient()


def write_llm(prompt: str, model: str = WRITE_MODEL) -> str:
    """Use MiniMax for content writing/translation."""
    cache_key = hashlib.md5(prompt.encode()).hexdigest()
    if cache_key in _WRITE_CACHE:
        return _WRITE_CACHE[cache_key]
    client = _minimax_client()
    result = client.complete(prompt, model)
    _WRITE_CACHE[cache_key] = result
    return result


def write_llm_batch(
    prompts: list[str],
    model: str = WRITE_MODEL,
    progress_callback=None,
) -> list[str]:
    """
    Translate multiple prompts in parallel using MiniMax.
    Returns list of results in same order as prompts.
    Skips cached prompts and caches new results.

    Args:
        prompts: List of prompt strings to send to LLM.
        model: Model name to use.
        progress_callback: Optional callable(done: int, total: int) called after each result.
    """
    cache_keys = [hashlib.md5(p.encode()).hexdigest() for p in prompts]
    missing_indices = [i for i, k in enumerate(cache_keys) if k not in _WRITE_CACHE]

    if not missing_indices:
        return [_WRITE_CACHE[k] for k in cache_keys]

    prompts_to_fetch = [prompts[i] for i in missing_indices]

    def _fetch(prompt: str) -> tuple[str, str]:
        import httpx, time
        api_key = os.environ.get("MINIMAX_API_KEY", "")
        base_url = os.environ.get("MINIMAX_BASE_URL", MINIMAX_BASE_URL).rstrip("/")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
        for attempt in range(3):
            try:
                r = httpx.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=_DEFAULT_TIMEOUT,
                )
                if r.status_code == 429:
                    # Rate limited: wait for the window to reset, then retry
                    if attempt < 2:
                        wait = 60 * (attempt + 1)  # 60s, 120s backoff
                        time.sleep(wait)
                        continue
                r.raise_for_status()
                result = r.json()["choices"][0]["message"]["content"]
                ck = hashlib.md5(prompt.encode()).hexdigest()
                _WRITE_CACHE[ck] = result
                return ck, result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 2:
                    time.sleep(60 * (attempt + 1))
                    continue
                raise
        # Return empty on final failure instead of raising, to let other requests complete
        return "", ""

    results_map: dict[str, str] = {}
    import time as _time
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        futures = {executor.submit(_fetch, p): p for p in prompts_to_fetch}
        for future in as_completed(futures):
            key, val = future.result()
            results_map[key] = val
            if progress_callback:
                progress_callback(len(results_map), len(prompts_to_fetch))

    out = []
    for i, k in enumerate(cache_keys):
        if k in _WRITE_CACHE:
            out.append(_WRITE_CACHE[k])
        else:
            out.append(results_map[k])
    return out


def eval_llm(prompt: str) -> str:
    """Use MiniMax for evaluation/scoring."""
    return write_llm(prompt, EVAL_MODEL)


def eval_llm_batch(prompts: list[str], model: str = EVAL_MODEL) -> list[str]:
    """Evaluate multiple prompts in parallel using MiniMax."""
    return write_llm_batch(prompts, model)
