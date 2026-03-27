from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class LegalSection(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    act_name: str
    dafa_no: Optional[str] = None
    title: Optional[str] = None
    content: str
    metadata: Dict = Field(default_factory=dict)
    verification_status: str = "pending" # pending/verified
    source_image_path: Optional[str] = None
    page_num: int
    symbol_found: Optional[str] = None
    amendment_history: Optional[str] = None

class SectionMetadata(BaseModel):
    symbols: Optional[str] = None
    footnote_text: Optional[str] = None
    has_amendment: bool = False
