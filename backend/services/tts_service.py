"""
TTS Configuration Service - Reading/Writing TTS settings from config.yaml
"""
import yaml
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from models.tts_config import TTSConfig, TTSConfigUpdate, TTSConfigResponse, AzureVoice

logger = logging.getLogger(__name__)


class TTSConfigService:
    """Service for managing TTS configuration"""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Default to project root config.yaml
            self.config_path = Path(__file__).parent.parent.parent / "config.yaml"
        else:
            self.config_path = config_path
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load config.yaml file"""
        if not self.config_path.exists():
            return {}
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _save_yaml(self, config: Dict[str, Any]):
        """Save config to config.yaml file"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    def _mask_api_key(self, api_key: Optional[str]) -> Optional[str]:
        """Mask API key for display"""
        if not api_key:
            return None
        if len(api_key) <= 8:
            return '*' * len(api_key)
        return api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
    
    def get_tts_config(self) -> TTSConfigResponse:
        """Get TTS configuration with masked API key"""
        config = self._load_yaml()
        
        # Map config.yaml keys to TTSConfig fields
        tts_method = config.get('tts_method', 'azure_tts')
        
        # Get method-specific settings
        api_key = None
        api_base = None
        voice = ''
        region = 'eastus'
        model = 'tts-1'
        speech_rate = 1.0
        
        if tts_method == 'azure_tts':
            api_key = config.get('azure_tts_key', '')
            region = config.get('azure_tts_region', 'eastus')
            voice = config.get('azure_voice', '')
        elif tts_method == 'openai_tts':
            api_key = config.get('openai_tts_api_key', config.get('api_key', ''))
            api_base = config.get('openai_tts_api_base', config.get('base_url', ''))
            voice = config.get('openai_voice', 'alloy')
            model = config.get('openai_tts_model', 'tts-1')
        elif tts_method == 'edge_tts':
            voice = config.get('edge_voice', '')
        elif tts_method in ('fish_tts', 'sf_fish_tts'):
            api_key = config.get('fish_tts_api_key', '')
            voice = config.get('fish_tts_character', '')
        elif tts_method == 'gpt_sovits':
            voice = config.get('gpt_sovits_character', '')
        
        speech_rate = config.get('speed_factor', 1.0)
        
        return TTSConfigResponse(
            method=tts_method,
            api_key_masked=self._mask_api_key(api_key),
            api_base=api_base,
            voice=voice,
            region=region,
            model=model,
            speech_rate=speech_rate
        )
    
    def update_tts_config(self, update: TTSConfigUpdate) -> TTSConfigResponse:
        """Update TTS configuration"""
        config = self._load_yaml()
        
        # Update method if provided
        if update.method is not None:
            config['tts_method'] = update.method
        
        current_method = config.get('tts_method', 'azure_tts')
        
        # Update method-specific settings
        if update.api_key is not None:
            if current_method == 'azure_tts':
                config['azure_tts_key'] = update.api_key
            elif current_method == 'openai_tts':
                config['openai_tts_api_key'] = update.api_key
            elif current_method in ('fish_tts', 'sf_fish_tts'):
                config['fish_tts_api_key'] = update.api_key
        
        if update.api_base is not None:
            if current_method == 'openai_tts':
                config['openai_tts_api_base'] = update.api_base
        
        if update.voice is not None:
            if current_method == 'azure_tts':
                config['azure_voice'] = update.voice
            elif current_method == 'openai_tts':
                config['openai_voice'] = update.voice
            elif current_method == 'edge_tts':
                config['edge_voice'] = update.voice
            elif current_method in ('fish_tts', 'sf_fish_tts'):
                config['fish_tts_character'] = update.voice
            elif current_method == 'gpt_sovits':
                config['gpt_sovits_character'] = update.voice
        
        if update.region is not None and current_method == 'azure_tts':
            config['azure_tts_region'] = update.region
        
        if update.model is not None and current_method == 'openai_tts':
            config['openai_tts_model'] = update.model
        
        if update.speech_rate is not None:
            config['speed_factor'] = update.speech_rate
        
        # Save config
        self._save_yaml(config)
        logger.info(f"TTS config updated: method={current_method}")
        
        return self.get_tts_config()
    
    async def get_azure_voices(self, api_key: str, region: str = 'eastus') -> List[AzureVoice]:
        """
        Return a curated list of commonly used Azure TTS voices.
        
        Note: 302.ai proxies Azure TTS but doesn't expose the voices/list API.
        This returns a pre-defined list of popular voices that work with 302.ai.
        """
        # Pre-defined list of popular Azure TTS voices that work with 302.ai
        voices_data = [
            # Chinese voices
            {"ShortName": "zh-CN-XiaoxiaoNeural", "DisplayName": "Xiaoxiao", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-YunxiNeural", "DisplayName": "Yunxi", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-YunjianNeural", "DisplayName": "Yunjian", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-XiaoyiNeural", "DisplayName": "Xiaoyi", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-YunyangNeural", "DisplayName": "Yunyang", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-XiaochenNeural", "DisplayName": "Xiaochen", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaohanNeural", "DisplayName": "Xiaohan", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaomengNeural", "DisplayName": "Xiaomeng", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaomoNeural", "DisplayName": "Xiaomo", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoqiuNeural", "DisplayName": "Xiaoqiu", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoruiNeural", "DisplayName": "Xiaorui", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoshuangNeural", "DisplayName": "Xiaoshuang", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoxuanNeural", "DisplayName": "Xiaoxuan", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoyanNeural", "DisplayName": "Xiaoyan", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaoyouNeural", "DisplayName": "Xiaoyou", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-XiaozhenNeural", "DisplayName": "Xiaozhen", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Female"},
            {"ShortName": "zh-CN-YunfengNeural", "DisplayName": "Yunfeng", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-YunhaoNeural", "DisplayName": "Yunhao", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-YunxiaNeural", "DisplayName": "Yunxia", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-YunyeNeural", "DisplayName": "Yunye", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            {"ShortName": "zh-CN-YunzeNeural", "DisplayName": "Yunze", "LocaleName": "Chinese (Mandarin, Simplified)", "Gender": "Male"},
            # Chinese (Taiwan)
            {"ShortName": "zh-TW-HsiaoChenNeural", "DisplayName": "HsiaoChen", "LocaleName": "Chinese (Taiwanese Mandarin)", "Gender": "Female"},
            {"ShortName": "zh-TW-YunJheNeural", "DisplayName": "YunJhe", "LocaleName": "Chinese (Taiwanese Mandarin)", "Gender": "Male"},
            {"ShortName": "zh-TW-HsiaoYuNeural", "DisplayName": "HsiaoYu", "LocaleName": "Chinese (Taiwanese Mandarin)", "Gender": "Female"},
            # Chinese (Cantonese)
            {"ShortName": "zh-HK-HiuMaanNeural", "DisplayName": "HiuMaan", "LocaleName": "Chinese (Cantonese)", "Gender": "Female"},
            {"ShortName": "zh-HK-WanLungNeural", "DisplayName": "WanLung", "LocaleName": "Chinese (Cantonese)", "Gender": "Male"},
            {"ShortName": "zh-HK-HiuGaaiNeural", "DisplayName": "HiuGaai", "LocaleName": "Chinese (Cantonese)", "Gender": "Female"},
            # English voices
            {"ShortName": "en-US-JennyNeural", "DisplayName": "Jenny", "LocaleName": "English (United States)", "Gender": "Female"},
            {"ShortName": "en-US-GuyNeural", "DisplayName": "Guy", "LocaleName": "English (United States)", "Gender": "Male"},
            {"ShortName": "en-US-AriaNeural", "DisplayName": "Aria", "LocaleName": "English (United States)", "Gender": "Female"},
            {"ShortName": "en-US-DavisNeural", "DisplayName": "Davis", "LocaleName": "English (United States)", "Gender": "Male"},
            {"ShortName": "en-US-AmberNeural", "DisplayName": "Amber", "LocaleName": "English (United States)", "Gender": "Female"},
            {"ShortName": "en-US-AnaNeural", "DisplayName": "Ana", "LocaleName": "English (United States)", "Gender": "Female"},
            {"ShortName": "en-US-AndrewNeural", "DisplayName": "Andrew", "LocaleName": "English (United States)", "Gender": "Male"},
            {"ShortName": "en-US-EmmaNeural", "DisplayName": "Emma", "LocaleName": "English (United States)", "Gender": "Female"},
            {"ShortName": "en-US-BrianNeural", "DisplayName": "Brian", "LocaleName": "English (United States)", "Gender": "Male"},
            {"ShortName": "en-GB-SoniaNeural", "DisplayName": "Sonia", "LocaleName": "English (United Kingdom)", "Gender": "Female"},
            {"ShortName": "en-GB-RyanNeural", "DisplayName": "Ryan", "LocaleName": "English (United Kingdom)", "Gender": "Male"},
            # Japanese voices
            {"ShortName": "ja-JP-NanamiNeural", "DisplayName": "Nanami", "LocaleName": "Japanese (Japan)", "Gender": "Female"},
            {"ShortName": "ja-JP-KeitaNeural", "DisplayName": "Keita", "LocaleName": "Japanese (Japan)", "Gender": "Male"},
            {"ShortName": "ja-JP-AoiNeural", "DisplayName": "Aoi", "LocaleName": "Japanese (Japan)", "Gender": "Female"},
            {"ShortName": "ja-JP-DaichiNeural", "DisplayName": "Daichi", "LocaleName": "Japanese (Japan)", "Gender": "Male"},
            {"ShortName": "ja-JP-MayuNeural", "DisplayName": "Mayu", "LocaleName": "Japanese (Japan)", "Gender": "Female"},
            {"ShortName": "ja-JP-NaokiNeural", "DisplayName": "Naoki", "LocaleName": "Japanese (Japan)", "Gender": "Male"},
            {"ShortName": "ja-JP-ShioriNeural", "DisplayName": "Shiori", "LocaleName": "Japanese (Japan)", "Gender": "Female"},
            # Korean voices
            {"ShortName": "ko-KR-SunHiNeural", "DisplayName": "SunHi", "LocaleName": "Korean (Korea)", "Gender": "Female"},
            {"ShortName": "ko-KR-InJoonNeural", "DisplayName": "InJoon", "LocaleName": "Korean (Korea)", "Gender": "Male"},
            {"ShortName": "ko-KR-BongJinNeural", "DisplayName": "BongJin", "LocaleName": "Korean (Korea)", "Gender": "Male"},
            {"ShortName": "ko-KR-GookMinNeural", "DisplayName": "GookMin", "LocaleName": "Korean (Korea)", "Gender": "Male"},
            {"ShortName": "ko-KR-JiMinNeural", "DisplayName": "JiMin", "LocaleName": "Korean (Korea)", "Gender": "Female"},
            {"ShortName": "ko-KR-SeoHyeonNeural", "DisplayName": "SeoHyeon", "LocaleName": "Korean (Korea)", "Gender": "Female"},
            {"ShortName": "ko-KR-SoonBokNeural", "DisplayName": "SoonBok", "LocaleName": "Korean (Korea)", "Gender": "Female"},
            {"ShortName": "ko-KR-YuJinNeural", "DisplayName": "YuJin", "LocaleName": "Korean (Korea)", "Gender": "Female"},
            # Other common languages
            {"ShortName": "fr-FR-DeniseNeural", "DisplayName": "Denise", "LocaleName": "French (France)", "Gender": "Female"},
            {"ShortName": "fr-FR-HenriNeural", "DisplayName": "Henri", "LocaleName": "French (France)", "Gender": "Male"},
            {"ShortName": "de-DE-KatjaNeural", "DisplayName": "Katja", "LocaleName": "German (Germany)", "Gender": "Female"},
            {"ShortName": "de-DE-ConradNeural", "DisplayName": "Conrad", "LocaleName": "German (Germany)", "Gender": "Male"},
            {"ShortName": "es-ES-ElviraNeural", "DisplayName": "Elvira", "LocaleName": "Spanish (Spain)", "Gender": "Female"},
            {"ShortName": "es-ES-AlvaroNeural", "DisplayName": "Alvaro", "LocaleName": "Spanish (Spain)", "Gender": "Male"},
            {"ShortName": "it-IT-ElsaNeural", "DisplayName": "Elsa", "LocaleName": "Italian (Italy)", "Gender": "Female"},
            {"ShortName": "it-IT-DiegoNeural", "DisplayName": "Diego", "LocaleName": "Italian (Italy)", "Gender": "Male"},
            {"ShortName": "pt-BR-FranciscaNeural", "DisplayName": "Francisca", "LocaleName": "Portuguese (Brazil)", "Gender": "Female"},
            {"ShortName": "pt-BR-AntonioNeural", "DisplayName": "Antonio", "LocaleName": "Portuguese (Brazil)", "Gender": "Male"},
            {"ShortName": "ru-RU-SvetlanaNeural", "DisplayName": "Svetlana", "LocaleName": "Russian (Russia)", "Gender": "Female"},
            {"ShortName": "ru-RU-DmitryNeural", "DisplayName": "Dmitry", "LocaleName": "Russian (Russia)", "Gender": "Male"},
        ]
        
        voices = []
        for voice in voices_data:
            voices.append(AzureVoice(
                name=voice.get('ShortName', ''),
                display_name=voice.get('DisplayName', ''),
                local_name=voice.get('DisplayName', ''),
                short_name=voice.get('ShortName', ''),
                gender=voice.get('Gender', 'Female'),
                locale=voice.get('ShortName', '').split('-')[0] + '-' + voice.get('ShortName', '').split('-')[1] if '-' in voice.get('ShortName', '') else '',
                locale_name=voice.get('LocaleName', ''),
                style_list=None,
                voice_type='Neural'
            ))
        
        return voices
