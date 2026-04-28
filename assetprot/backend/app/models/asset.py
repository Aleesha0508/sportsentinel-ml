from pydantic import BaseModel


class AssetCreate(BaseModel):
    title: str
    sport: str
    owner: str


class AssetResponse(BaseModel):
    asset_id: str
    title: str
    sport: str
    owner: str
    status: str
    created_at: str
