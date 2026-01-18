import os
import json
import time
from threading import Lock
import json_repair
from openai import OpenAI
from core.utils.config_utils import load_key
from rich import print as rprint
from core.utils.decorator import except_handler

# ------------
# cache gpt response
# ------------

LOCK = Lock()
GPT_LOG_FOLDER = 'output/gpt_log'

def _save_cache(model, prompt, resp_content, resp_type, resp, message=None, log_title="default", duration_seconds=None, cached=False):
    """Save LLM response to cache file with timing information.
    
    Args:
        model: The model name used for the request
        prompt: The input prompt
        resp_content: Raw response content string
        resp_type: Response type (json, str, etc.)
        resp: Parsed response object
        message: Optional error message
        log_title: Log file title/name
        duration_seconds: Time taken for the API call (None if cache hit)
        cached: Whether this was a cache hit
    """
    with LOCK:
        logs = []
        file = os.path.join(GPT_LOG_FOLDER, f"{log_title}.json")
        os.makedirs(os.path.dirname(file), exist_ok=True)
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        
        log_entry = {
            "model": model, 
            "prompt": prompt, 
            "resp_content": resp_content, 
            "resp_type": resp_type, 
            "resp": resp, 
            "message": message,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration_seconds": duration_seconds,
            "cached": cached
        }
        logs.append(log_entry)
        
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=4)

def _load_cache(prompt, resp_type, log_title):
    with LOCK:
        file = os.path.join(GPT_LOG_FOLDER, f"{log_title}.json")
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                for item in json.load(f):
                    if item["prompt"] == prompt and item["resp_type"] == resp_type:
                        return item["resp"]
        return False

# ------------
# ask gpt once
# ------------

def _emit_llm_log(message: str, duration_ms: int = None, level: str = "INFO"):
    """Emit LLM log to LogStore if running in backend context."""
    try:
        from backend.api.deps import get_log_store
        log_store = get_log_store()
        log_store.add(message=message, level=level, source="llm", duration_ms=duration_ms)
    except ImportError:
        # Not running in backend context, skip logging to LogStore
        pass
    except Exception:
        # LogStore not available or not initialized, skip
        pass

@except_handler("GPT request failed", retry=5)
def ask_gpt(prompt, resp_type=None, valid_def=None, log_title="default"):
    if not load_key("api.key"):
        raise ValueError("API key is not set")
    # check cache
    cached_resp = _load_cache(prompt, resp_type, log_title)
    if cached_resp:
        rprint("use cache response")
        # Log cache hit
        _emit_llm_log(f"LLM cache hit for {log_title}", level="INFO")
        return cached_resp

    model = load_key("api.model")
    base_url = load_key("api.base_url")
    if 'ark' in base_url:
        base_url = "https://ark.cn-beijing.volces.com/api/v3" # huoshan base url
    elif 'v1' not in base_url:
        base_url = base_url.strip('/') + '/v1'
    client = OpenAI(api_key=load_key("api.key"), base_url=base_url)
    response_format = {"type": "json_object"} if resp_type == "json" and load_key("api.llm_support_json") else None

    messages = [{"role": "user", "content": prompt}]

    params = dict(
        model=model,
        messages=messages,
        response_format=response_format,
        timeout=300
    )
    
    # Time the API call
    start_time = time.perf_counter()
    resp_raw = client.chat.completions.create(**params)
    end_time = time.perf_counter()
    
    duration_seconds = round(end_time - start_time, 3)
    duration_ms = int(duration_seconds * 1000)

    # process and return full result
    resp_content = resp_raw.choices[0].message.content
    if resp_type == "json":
        resp = json_repair.loads(resp_content)
    else:
        resp = resp_content
    
    # Log the LLM request with timing
    prompt_preview = prompt[:50] + "..." if len(prompt) > 50 else prompt
    _emit_llm_log(f"LLM request ({log_title}): {prompt_preview}", duration_ms=duration_ms)
    rprint(f"[dim]LLM request took {duration_seconds}s[/dim]")
    
    # check if the response format is valid
    if valid_def:
        valid_resp = valid_def(resp)
        if valid_resp['status'] != 'success':
            _save_cache(model, prompt, resp_content, resp_type, resp, log_title="error", message=valid_resp['message'], duration_seconds=duration_seconds, cached=False)
            raise ValueError(f"❎ API response error: {valid_resp['message']}")

    _save_cache(model, prompt, resp_content, resp_type, resp, log_title=log_title, duration_seconds=duration_seconds, cached=False)
    return resp


if __name__ == '__main__':
    from rich import print as rprint
    
    result = ask_gpt("""test respond ```json\n{\"code\": 200, \"message\": \"success\"}\n```""", resp_type="json")
    rprint(f"Test json output result: {result}")
