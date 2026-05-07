from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

class LayoutBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float

class LayoutItem(BaseModel):
    id: int
    box: List[List[float]] = Field(..., description="[[x1,y1], [x2,y1], [x2,y2], [x1,y2]]")
    text: str
    confidence: float
    type: str = Field("text", description="text, table, header, footer, etc.")

class LayoutResult(BaseModel):
    file_name: str
    file_token: Optional[str] = Field(None, description="Token/ID to retrieve file for subsequent steps")
    image_base64: str = Field(..., description="Base64 encoded image for visualization")
    image_width: int
    image_height: int
    regions: List[LayoutItem]
    processing_time_ms: float
