"""
Config Service - Business logic for configuration management
"""
import os
import yaml
from ruamel.yaml import YAML
from pathlib import Path
from typing import Optional
import httpx

from models import Configuration, ConfigurationUpdate, ApiValidateResponse
from api.deps import get_config_file


class ConfigService:
    """Service for configuration management"""
    
    def __init__(self):
        self.config_file = get_config_file()
    
    def load_config(self) -> Configuration:
        """Load configuration from config.yaml"""
        if not self.config_file.exists():
            return Configuration()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            return self._yaml_to_config(data)
        except Exception as e:
            raise ValueError(f"Failed to load config: {e}")
    
    def update_config(self, update: ConfigurationUpdate) -> Configuration:
        """Update configuration - preserves comments and original formatting"""
        # Use ruamel.yaml to preserve comments and formatting
        ruamel = YAML()
        ruamel.preserve_quotes = True
        ruamel.indent(mapping=2, sequence=4, offset=2)
        
        # Load raw YAML preserving comments
        raw_yaml = {}
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                raw_yaml = ruamel.load(f) or {}
        
        # Helper function to convert camelCase to snake_case
        def to_snake_case(name: str) -> str:
            import re
            # Insert underscore before uppercase letters (except at start) and convert to lowercase
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        
        # Apply updates only for fields that were explicitly set
        # Use by_alias=False to get snake_case keys from Pydantic model
        update_dict = update.model_dump(exclude_unset=True, by_alias=False)
        
        # Fields that should be removed from YAML when set to None
        nullable_fields = {'time_gap_threshold', 'timeGapThreshold'}
        
        # Fields that map to nested YAML structure
        nested_field_mapping = {
            'cjk_split': ('subtitle', 'cjk_split'),  # cjk_split -> subtitle.cjk_split
        }
        
        # Pydantic field names that differ from YAML key names (nested keys)
        # Maps pydantic_field_name -> yaml_key_name for nested dict values
        yaml_key_mapping = {
            'whisperX_model': 'model',      # whisper.whisperX_model -> whisper.model
            'whisper_x_model': 'model',     # Also handle snake_case version
            'method': 'runtime',            # whisper.method -> whisper.runtime
        }
        
        for key, value in update_dict.items():
            # Ensure key is in snake_case for YAML storage
            yaml_key = to_snake_case(key)
            
            # Handle nullable fields - remove from YAML if None
            if key in nullable_fields or yaml_key in nullable_fields:
                if value is None:
                    # Remove the key from YAML to disable the feature
                    if yaml_key in raw_yaml:
                        del raw_yaml[yaml_key]
                    continue
            
            # Handle nested field mappings (like cjk_split -> subtitle.cjk_split)
            if yaml_key in nested_field_mapping:
                parent_key, child_key = nested_field_mapping[yaml_key]
                if parent_key not in raw_yaml:
                    raw_yaml[parent_key] = {}
                raw_yaml[parent_key][child_key] = value
                continue
            
            if value is not None:
                if isinstance(value, dict) and yaml_key in raw_yaml and isinstance(raw_yaml.get(yaml_key), dict):
                    # Merge nested dicts - only update specified keys
                    for sub_key, sub_value in value.items():
                        if sub_value is not None:
                            # Convert nested keys to snake_case, then apply yaml_key_mapping
                            yaml_sub_key = to_snake_case(sub_key)
                            # Check if there's a special mapping for this field
                            if yaml_sub_key in yaml_key_mapping:
                                yaml_sub_key = yaml_key_mapping[yaml_sub_key]
                            elif sub_key in yaml_key_mapping:
                                yaml_sub_key = yaml_key_mapping[sub_key]
                            raw_yaml[yaml_key][yaml_sub_key] = sub_value
                else:
                    raw_yaml[yaml_key] = value
        
        # Save to file - preserve original structure and comments
        with open(self.config_file, 'w', encoding='utf-8') as f:
            ruamel.dump(raw_yaml, f)
        
        # Apply network settings immediately to environment variables
        self._apply_network_settings(update_dict)
        
        return self.load_config()
    
    def _apply_network_settings(self, update_dict: dict) -> None:
        """Apply network-related settings to environment variables immediately"""
        # Handle http_proxy
        if 'http_proxy' in update_dict:
            http_proxy = update_dict['http_proxy']
            if http_proxy:
                os.environ["HTTP_PROXY"] = http_proxy
                os.environ["HTTPS_PROXY"] = http_proxy
                os.environ["HF_HUB_HTTP_PROXY"] = http_proxy
            else:
                # Clear proxy if set to empty
                os.environ.pop("HTTP_PROXY", None)
                os.environ.pop("HTTPS_PROXY", None)
                os.environ.pop("HF_HUB_HTTP_PROXY", None)
        
        # Handle hf_mirror
        if 'hf_mirror' in update_dict:
            hf_mirror = update_dict['hf_mirror']
            if hf_mirror:
                os.environ["HF_ENDPOINT"] = hf_mirror
            else:
                # Use default mirror if cleared
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    
    async def validate_api_key(self, key: str, base_url: str, model: str) -> ApiValidateResponse:
        """Validate API key by making a test request"""
        # Ensure base_url doesn't end with /v1/chat/completions
        base_url = base_url.rstrip('/')
        if not base_url.endswith('/v1'):
            base_url = f"{base_url}/v1"
        
        url = f"{base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    return ApiValidateResponse(valid=True, message="API Key is valid")
                elif response.status_code == 401:
                    return ApiValidateResponse(valid=False, message="Invalid API Key")
                elif response.status_code == 404:
                    return ApiValidateResponse(valid=False, message=f"Model {model} not found")
                else:
                    return ApiValidateResponse(
                        valid=False, 
                        message=f"API error: {response.status_code} - {response.text[:200]}"
                    )
        except httpx.TimeoutException:
            return ApiValidateResponse(valid=False, message="Request timed out")
        except Exception as e:
            return ApiValidateResponse(valid=False, message=str(e))
    
    def _yaml_to_config(self, data: dict) -> Configuration:
        """Convert YAML data to Configuration model"""
        api_config = None
        if 'api' in data:
            api_data = data['api']
            from models import ApiConfig
            api_config = ApiConfig(
                key=api_data.get('key', ''),
                base_url=api_data.get('base_url', 'https://api.openai.com'),
                model=api_data.get('model', 'gpt-4o-mini'),
                llm_support_json=api_data.get('llm_support_json', True)
            )
        
        whisper_config = None
        source_language = data.get('source_language', 'en')  # Default fallback
        if 'whisper' in data:
            whisper_data = data['whisper']
            # Get source language from whisper.language if available
            source_language = whisper_data.get('language', source_language)
            from models import WhisperConfig
            whisper_config = WhisperConfig(
                method=whisper_data.get('runtime', 'local'),
                whisperX_model=whisper_data.get('model', 'large-v3'),
                whisperX_302_api_key=whisper_data.get('whisperX_302_api_key'),
                elevenlabs_api_key=whisper_data.get('elevenlabs_api_key'),
                use_segment_mode=whisper_data.get('use_segment_mode', False)
            )
        
        # Get TTS configurations from nested structures
        sf_fish_tts = data.get('sf_fish_tts', {})
        openai_tts = data.get('openai_tts', {})
        azure_tts = data.get('azure_tts', {})
        fish_tts = data.get('fish_tts', {})
        gpt_sovits = data.get('gpt_sovits', {})
        edge_tts = data.get('edge_tts', {})
        sf_cosyvoice2 = data.get('sf_cosyvoice2', {})
        f5tts = data.get('f5tts', {})
        
        # Get subtitle config
        subtitle_data = data.get('subtitle', {})
        from models import SubtitleConfig
        subtitle_config = SubtitleConfig(
            max_length=subtitle_data.get('max_length', 75),
            target_multiplier=subtitle_data.get('target_multiplier', 1.2)
        )
        
        return Configuration(
            display_language=data.get('display_language', '简体中文'),
            api=api_config or Configuration().api,
            resolution=data.get('resolution', '1080'),
            source_language=source_language,
            target_language=data.get('target_language', '简体中文'),
            max_split_length=data.get('max_split_length', 12 if source_language == 'ja' else 20),
            time_gap_threshold=data.get('time_gap_threshold'),
            demucs=data.get('demucs', False),
            burn_subtitles=data.get('burn_subtitles', True),
            cjk_split=subtitle_data.get('cjk_split', False),
            subtitle=subtitle_config,
            whisper=whisper_config or Configuration().whisper,
            tts_method=data.get('tts_method', 'edge_tts'),
            # OpenAI TTS
            openai_tts_api_key=openai_tts.get('api_key'),
            openai_voice=openai_tts.get('voice', 'alloy'),
            # Azure TTS
            azure_key=azure_tts.get('api_key'),
            azure_region=azure_tts.get('region'),
            azure_voice=azure_tts.get('voice', 'zh-CN-XiaoxiaoNeural'),
            # Fish TTS
            fish_tts_api_key=fish_tts.get('api_key'),
            fish_tts_character=fish_tts.get('character', 'AD学姐'),
            # SiliconFlow Fish TTS
            sf_fish_tts_api_key=sf_fish_tts.get('api_key'),
            sf_fish_tts_mode=sf_fish_tts.get('mode', 'preset'),
            sf_fish_tts_voice=sf_fish_tts.get('voice', 'anna'),
            # GPT-SoVITS
            sovits_character=gpt_sovits.get('character', ''),
            gpt_sovits_refer_mode=gpt_sovits.get('refer_mode', 3),
            # Edge TTS
            edge_tts_voice=edge_tts.get('voice', 'zh-CN-XiaoxiaoNeural'),
            # SiliconFlow CosyVoice2
            sf_cosyvoice2_api_key=sf_cosyvoice2.get('api_key'),
            # F5-TTS
            f5tts_api_key=f5tts.get('302_api'),
            # Custom TTS
            custom_tts_api_key=data.get('custom_tts_api_key'),
            custom_tts_base_url=data.get('custom_tts_base_url'),
            custom_tts_model=data.get('custom_tts_model'),
            # Legacy
            sf_api_key=data.get('sf_api_key'),
            # Other
            ytb_cookies_path=data.get('ytb_cookies_path'),
            http_proxy=data.get('http_proxy'),
            hf_mirror=data.get('hf_mirror')
        )
    
    def _config_to_yaml(self, config: dict) -> dict:
        """Convert Configuration dict to YAML-friendly format"""
        yaml_data = {}
        
        # Map back to original yaml structure
        yaml_data['display_language'] = config.get('display_language', '简体中文')
        
        if 'api' in config and config['api']:
            yaml_data['api'] = {
                'key': config['api'].get('key', ''),
                'base_url': config['api'].get('base_url', 'https://api.openai.com'),
                'model': config['api'].get('model', 'gpt-4o-mini'),
                'llm_support_json': config['api'].get('llm_support_json', True)
            }
        
        yaml_data['resolution'] = config.get('resolution', '1080')
        # target_language is at root level in config.yaml
        yaml_data['target_language'] = config.get('target_language', '简体中文')
        yaml_data['demucs'] = config.get('demucs', False)
        yaml_data['burn_subtitles'] = config.get('burn_subtitles', True)
        
        # source_language maps to whisper.language in config.yaml
        source_language = config.get('source_language', 'en')
        
        if 'whisper' in config and config['whisper']:
            yaml_data['whisper'] = {
                'runtime': config['whisper'].get('method', 'local'),
                'model': config['whisper'].get('whisperX_model', 'large-v3'),
                'language': source_language,  # Source language goes into whisper.language
                'use_segment_mode': config['whisper'].get('use_segment_mode', False),
            }
            if config['whisper'].get('whisperX_302_api_key'):
                yaml_data['whisper']['whisperX_302_api_key'] = config['whisper']['whisperX_302_api_key']
            if config['whisper'].get('elevenlabs_api_key'):
                yaml_data['whisper']['elevenlabs_api_key'] = config['whisper']['elevenlabs_api_key']
        else:
            # If no whisper config, still set the language
            yaml_data['whisper'] = {
                'runtime': 'local',
                'model': 'large-v3',
                'language': source_language,
                'use_segment_mode': False,
            }
        
        yaml_data['tts_method'] = config.get('tts_method', 'edge_tts')
        
        # Optional TTS configs
        optional_keys = [
            'openai_tts_api_key', 'openai_voice', 'azure_key', 'azure_region',
            'azure_voice', 'fish_tts_api_key', 'fish_tts_character', 'sf_api_key',
            'sovits_character', 'gpt_sovits_refer_mode', 'edge_tts_voice',
            'custom_tts_api_key', 'custom_tts_base_url', 'custom_tts_model',
            'ytb_cookies_path', 'http_proxy', 'hf_mirror'
        ]
        
        for key in optional_keys:
            if key in config and config[key]:
                yaml_data[key] = config[key]
        
        return yaml_data
