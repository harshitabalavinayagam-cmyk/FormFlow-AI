from pydantic import BaseModel, Field
from typing import List, Optional


class FormField(BaseModel):
    name: str
    label: str
    type: str
    required: bool = False
    options: Optional[List[str]] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None


class FormSchema(BaseModel):
    title: str
    description: str
    fields: List[FormField]