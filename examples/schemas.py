from pydantic import BaseModel, Field
from typing import List

class AnalysisSchema(BaseModel):
    summary: str = Field(description="A brief summary of the text")
    topics: list[str] = Field(description="List of identified topics")
    sentiment: str = Field(description="Overall sentiment: Positive, Negative, or Neutral")

class UserProfile(BaseModel):
    username: str
    is_active: bool

class MediaBuyerSchema(BaseModel):
    campaign_structure: dict
    ad_copies: list[str]
    creative_ideas: list[str]
    testing_strategy: dict
    optimization_plan: dict
    kpis: list[str]
