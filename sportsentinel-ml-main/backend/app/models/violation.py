from typing import Optional
from pydantic import BaseModel, Field


class ModalityScores(BaseModel):
    visual: float = 0.0
    audio: float = 0.0
    text: float = 0.0


class MatchedTimestamps(BaseModel):
    query_start: float = 0.0
    query_end: float = 0.0


class ViolationBase(BaseModel):
    query_asset_id: str
    matched_asset_id: Optional[str] = None
    matched_title: Optional[str] = None
    platform: str
    source_url: str = ""
    query_filename: str
    query_storage_path: str
    content_type: str = "application/octet-stream"
    confidence: float = 0.0
    similarity_score: float = 0.0
    violation_type: str = "none"
    modality_scores: ModalityScores = Field(default_factory=ModalityScores)
    matched_timestamps: MatchedTimestamps = Field(default_factory=MatchedTimestamps)
    explanation: str = ""
    severity: str = "medium"
    status: str = "open"


class ViolationCreate(ViolationBase):
    violation_id: str
    created_at: str


class ViolationResponse(ViolationCreate):
    pass