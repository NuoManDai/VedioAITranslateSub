"""
Configuration API routes
"""
from fastapi import APIRouter, HTTPException

from models import Configuration, ConfigurationUpdate, ApiValidateRequest, ApiValidateResponse
from services.config_service import ConfigService

router = APIRouter()
config_service = ConfigService()


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
