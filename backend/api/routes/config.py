"""
Configuration API routes
"""
from fastapi import APIRouter, HTTPException

from models import Configuration, ConfigurationUpdate, ApiValidateRequest, ApiValidateResponse
from models.tts_config import TTSConfigUpdate, TTSConfigResponse, AzureVoiceListResponse
from services.config_service import ConfigService
from services.tts_service import TTSConfigService

router = APIRouter()
config_service = ConfigService()
tts_service = TTSConfigService()


@router.get("", response_model=Configuration)
async def get_config():
    """
    获取系统配置
    """
    try:
        config = config_service.load_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=Configuration)
async def update_config(update: ConfigurationUpdate):
    """
    更新系统配置
    """
    try:
        config = config_service.update_config(update)
        return config
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-api", response_model=ApiValidateResponse)
async def validate_api_key(request: ApiValidateRequest):
    """
    验证 API 密钥有效性
    """
    try:
        result = await config_service.validate_api_key(
            request.key,
            request.base_url,
            request.model
        )
        return result
    except Exception as e:
        return ApiValidateResponse(valid=False, message=str(e))


# ============ TTS Configuration API ============

@router.get("/tts", response_model=TTSConfigResponse)
async def get_tts_config():
    """
    获取 TTS 配置（API Key 已掩码）
    """
    try:
        return tts_service.get_tts_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tts", response_model=TTSConfigResponse)
async def update_tts_config(update: TTSConfigUpdate):
    """
    更新 TTS 配置
    """
    try:
        return tts_service.update_tts_config(update)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tts/azure/voices", response_model=AzureVoiceListResponse)
async def get_azure_voices(region: str = 'eastus'):
    """
    获取 Azure TTS 预设语音列表
    
    返回常用的 Azure TTS 语音预设列表，无需 API Key。
    这些语音均兼容 302.ai 代理服务。
    """
    try:
        voices = await tts_service.get_azure_voices("", region)
        return AzureVoiceListResponse(voices=voices, total=len(voices))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Azure voice presets: {str(e)}")
