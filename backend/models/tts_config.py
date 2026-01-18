"""
TTS Configuration models
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal, List


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase"""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


TTSMethod = Literal[
    'azure_tts', 
    'openai_tts', 
    'edge_tts', 
    'fish_tts', 
    'sf_fish_tts',
    'gpt_sovits', 
    'custom_tts'
]


class TTSConfig(BaseModel):
    """TTS 服务配置模型"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    method: TTSMethod = Field(default='azure_tts', description="TTS 方法选择")
    api_key: Optional[str] = Field(None, description="API 密钥")
    api_base: Optional[str] = Field(None, description="API 基础 URL")
    voice: str = Field(default='', description="选择的语音名称")
    region: Optional[str] = Field(default='eastus', description="Azure 区域 (仅 Azure TTS)")
    model: Optional[str] = Field(default='tts-1', description="模型名称 (仅 OpenAI TTS)")
    speech_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍率")


class TTSConfigUpdate(BaseModel):
    """TTS 配置更新请求"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    method: Optional[TTSMethod] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    voice: Optional[str] = None
    region: Optional[str] = None
    model: Optional[str] = None
    speech_rate: Optional[float] = Field(None, ge=0.5, le=2.0)


class TTSConfigResponse(BaseModel):
    """TTS 配置响应（API Key 掩码）"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    method: TTSMethod
    api_key_masked: Optional[str] = Field(None, description="掩码后的 API 密钥")
    api_base: Optional[str] = None
    voice: str
    region: Optional[str] = None
    model: Optional[str] = None
    speech_rate: float = 1.0


class AzureVoice(BaseModel):
    """Azure TTS 语音信息"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    name: str = Field(..., description="完整语音名称")
    display_name: str = Field(..., description="显示名称")
    local_name: str = Field(..., description="本地化名称")
    short_name: str = Field(..., description="短名称")
    gender: Literal['Male', 'Female'] = Field(..., description="性别")
    locale: str = Field(..., description="语言区域")
    locale_name: str = Field(..., description="语言区域名称")
    style_list: Optional[List[str]] = Field(None, description="支持的风格列表")
    voice_type: str = Field(..., description="语音类型: Neural, Standard")


class AzureVoiceListResponse(BaseModel):
    """Azure 语音列表响应"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    
    voices: List[AzureVoice] = Field(default_factory=list, description="语音列表")
    grouped_by_locale: dict[str, List[AzureVoice]] = Field(
        default_factory=dict, 
        description="按语言区域分组的语音列表"
    )
