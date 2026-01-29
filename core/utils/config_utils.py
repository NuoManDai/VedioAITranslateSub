from ruamel.yaml import YAML
import threading
import os

# 获取项目根目录（config.yaml 所在位置）
_CORE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(_CORE_DIR)
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config.yaml')
CANCEL_FLAG_FILE = os.path.join(PROJECT_ROOT, 'output', '.cancel_requested')

lock = threading.Lock()

yaml = YAML()
yaml.preserve_quotes = True

# -----------------------
# load & update config
# -----------------------

def load_key(key):
    with lock:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file)

    keys = key.split('.')
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            raise KeyError(f"Key '{k}' not found in configuration")
    return value

def update_key(key, new_value):
    with lock:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as file:
            data = yaml.load(file)

        keys = key.split('.')
        current = data
        for k in keys[:-1]:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False

        if isinstance(current, dict) and keys[-1] in current:
            current[keys[-1]] = new_value
            with open(CONFIG_PATH, 'w', encoding='utf-8') as file:
                yaml.dump(data, file)
            return True
        else:
            raise KeyError(f"Key '{keys[-1]}' not found in configuration")

# -----------------------
# Cancel flag operations
# -----------------------

class CancelledError(Exception):
    """Exception raised when processing is cancelled"""
    pass

def set_cancel_flag():
    """Set the cancel flag (create the flag file)"""
    os.makedirs(os.path.dirname(CANCEL_FLAG_FILE), exist_ok=True)
    with open(CANCEL_FLAG_FILE, 'w') as f:
        f.write('1')

def clear_cancel_flag():
    """Clear the cancel flag (remove the flag file)"""
    if os.path.exists(CANCEL_FLAG_FILE):
        os.remove(CANCEL_FLAG_FILE)

def is_cancelled():
    """Check if processing has been cancelled"""
    return os.path.exists(CANCEL_FLAG_FILE)

def check_cancelled():
    """Check if cancelled and raise exception if so"""
    if is_cancelled():
        raise CancelledError("Processing was cancelled by user")
        
# basic utils
def get_joiner(language):
    if language in load_key('language_split_with_space'):
        return " "
    elif language in load_key('language_split_without_space'):
        return ""
    else:
        raise ValueError(f"Unsupported language code: {language}")

# Language code to full name mapping for LLM prompts
LANGUAGE_CODE_MAP = {
    'ja': 'Japanese',
    'zh': 'Chinese', 
    'ko': 'Korean',
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'th': 'Thai',
    'vi': 'Vietnamese',
    'id': 'Indonesian',
    'ms': 'Malay',
    'tr': 'Turkish',
    'pl': 'Polish',
    'nl': 'Dutch',
    'sv': 'Swedish',
    'da': 'Danish',
    'no': 'Norwegian',
    'fi': 'Finnish',
    'cs': 'Czech',
    'hu': 'Hungarian',
    'el': 'Greek',
    'he': 'Hebrew',
    'uk': 'Ukrainian',
    'ro': 'Romanian',
    'bg': 'Bulgarian',
}

def get_language_name(lang_code: str) -> str:
    """Convert language code (e.g., 'ja') to full name (e.g., 'Japanese') for LLM prompts.
    If already a full name or unknown code, return as-is."""
    if not lang_code:
        return lang_code
    code_lower = lang_code.lower()
    return LANGUAGE_CODE_MAP.get(code_lower, lang_code)

if __name__ == "__main__":
    print(load_key('language_split_with_space'))
