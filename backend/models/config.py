"""
Configuration data model
映射 config.yaml 配置文件
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
import yaml
from pathlib import Path


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class ApiConfig(BaseModel):
    """API 配置"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    key: str = Field(default='', description="API 密钥")
    base_url: str = Field(default='https://api.openai.com', description="API 基础 URL")
    model: str = Field(default='gpt-4o-mini', description="模型名称")
    llm_support_json: bool = Field(default=True, description="是否支持 JSON 模式")


class WhisperConfig(BaseModel):
    """Whisper 配置"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    method: str = Field(default='whisperX_local', description="Whisper 方法")
    whisperX_model: str = Field(default='large-v2', description="WhisperX 模型")
    whisperX_302_api_key: Optional[str] = Field(None, description="302.ai API 密钥")
    elevenlabs_api_key: Optional[str] = Field(None, description="ElevenLabs API 密钥")


class Configuration(BaseModel):
    """系统配置模型"""
    # 显示语言
    display_language: str = Field(default='简体中文', description="界面显示语言")
    
    # API 配置
    api: ApiConfig = Field(default_factory=ApiConfig)
    
    # 视频处理设置
    resolution: str = Field(default='1080', description="视频分辨率")
    
    # 字幕设置
    source_language: str = Field(default='en', description="源语言")
    target_language: str = Field(default='简体中文', description="目标语言")
    demucs: bool = Field(default=False, description="是否启用人声分离")
    burn_subtitles: bool = Field(default=True, description="是否烧录字幕")
    
    # Whisper 设置
    whisper: WhisperConfig = Field(default_factory=WhisperConfig)
    
    # TTS 设置
    tts_method: str = Field(default='openai_tts', description="TTS 方法")
    openai_tts_api_key: Optional[str] = Field(None, description="OpenAI TTS API Key")
    openai_voice: str = Field(default='alloy', description="OpenAI 语音")
    azure_key: Optional[str] = Field(None, description="Azure Key")
    azure_region: Optional[str] = Field(None, description="Azure Region")
    azure_voice: str = Field(default='zh-CN-XiaoxiaoNeural', description="Azure 语音")
    fish_tts_api_key: Optional[str] = Field(None, description="Fish TTS API Key")
    fish_tts_character: str = Field(default='', description="Fish TTS 角色")
    sf_api_key: Optional[str] = Field(None, description="SiliconFlow API Key")
    sovits_character: str = Field(default='', description="SoVITS 角色")
    gpt_sovits_refer_mode: int = Field(default=1, description="GPT-SoVITS 参考模式")
    edge_tts_voice: str = Field(default='zh-CN-XiaoxiaoNeural', description="Edge TTS 语音")
    custom_tts_api_key: Optional[str] = Field(None, description="Custom TTS API Key")
    custom_tts_base_url: Optional[str] = Field(None, description="Custom TTS Base URL")
    custom_tts_model: Optional[str] = Field(None, description="Custom TTS Model")
    
    # YouTube cookies
    ytb_cookies_path: Optional[str] = Field(None, description="YouTube Cookies 路径")
    
    # Network proxy
    http_proxy: Optional[str] = Field(None, description="HTTP 代理地址 (如 http://127.0.0.1:10809)")
    hf_mirror: Optional[str] = Field(None, description="HuggingFace 镜像地址")

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True  # Allow both snake_case and camelCase
    )


class ConfigurationUpdate(BaseModel):
    """配置更新模型，所有字段可选"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    display_language: Optional[str] = None
    api: Optional[ApiConfig] = None
    resolution: Optional[str] = None
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    demucs: Optional[bool] = None
    burn_subtitles: Optional[bool] = None
    whisper: Optional[WhisperConfig] = None
    tts_method: Optional[str] = None
    openai_tts_api_key: Optional[str] = None
    openai_voice: Optional[str] = None
    azure_key: Optional[str] = None
    azure_region: Optional[str] = None
    azure_voice: Optional[str] = None
    fish_tts_api_key: Optional[str] = None
    fish_tts_character: Optional[str] = None
    sf_api_key: Optional[str] = None
    sovits_character: Optional[str] = None
    gpt_sovits_refer_mode: Optional[int] = None
    edge_tts_voice: Optional[str] = None
    custom_tts_api_key: Optional[str] = None
    custom_tts_base_url: Optional[str] = None
    custom_tts_model: Optional[str] = None
    ytb_cookies_path: Optional[str] = None
    http_proxy: Optional[str] = None
    hf_mirror: Optional[str] = None


class ApiValidateRequest(BaseModel):
    """API 验证请求模型"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    key: str = Field(..., description="API 密钥")
    base_url: str = Field(..., description="API 基础 URL")
    model: str = Field(..., description="模型名称")


class ApiValidateResponse(BaseModel):
    """API 验证响应模型"""
    valid: bool = Field(..., description="是否有效")
    message: str = Field(..., description="验证结果消息")
