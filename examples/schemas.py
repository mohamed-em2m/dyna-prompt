from pydantic import BaseModel, Field
from typing import List

class AnalysisSchema(BaseModel):
    summary: str = Field(description="A brief summary of the text")
    topics: List[str] = Field(description="List of identified topics")
    sentiment: str = Field(description="Overall sentiment: Positive, Negative, or Neutral")

class UserProfile(BaseModel):
    username: str
    is_active: bool
