from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal

class ReplaceBackgroundRelightInput(BaseModel):
    # Now expecting URLs instead of arbitrary strings
    subject_image: HttpUrl
    background_prompt: str
    background_reference: Optional[HttpUrl] = None

    foreground_prompt: Optional[str] = ""
    negative_prompt: Optional[str] = ""
    preserve_original_subject: float = Field(0.95, ge=0, le=1)
    original_background_depth: float = Field(0.75, ge=0, le=1)
    keep_original_background: bool = False

    light_source_strength: float = Field(0, ge=0, le=1)
    light_reference: Optional[HttpUrl] = None
    light_source_direction: Literal["none", "left", "right", "above", "below"] = "none"

    seed: int = 0
    output_format: Literal["webp", "jpeg", "png"] = "png"
    username: Optional[str] = None
