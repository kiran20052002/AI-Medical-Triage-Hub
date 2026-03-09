from typing import List, Optional
from datetime import datetime
from beanie import Document, Link, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from pydantic.alias_generators import to_camel

class BaseConfig(BaseModel):
    class Config:
        alias_generator = to_camel
        populate_by_name = True


class Patient(Document):
    email: EmailStr
    password: str
    role: str = "patient"
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "patients"

class Doctor(Document):
    email: EmailStr
    password: str
    role: str = "doctor"
    specialist: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "doctors"

class Report(Document):
    content: dict
    formatted_report: Optional[str] = Field(default=None, alias="formattedReport")
    embedding: List[float]
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "reports"

class Ticket(Document):
    title: str
    description: str
    status: str = "TODO"
    created_by: PydanticObjectId = Field(alias="createdBy")
    assigned_to: Optional[PydanticObjectId] = Field(default=None, alias="assignedTo")
    priority: Optional[str] = None
    channel_id: Optional[str] = Field(default=None, alias="channelId")
    connection_status: Optional[str] = Field(default=None, alias="connectionStatus")
    deadline: Optional[datetime] = None
    helpful_notes: Optional[str] = Field(default=None, alias="helpfulNotes")
    suggested_solution: Optional[str] = Field(default=None, alias="suggestedSolution")
    specialist: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

    class Settings(BaseConfig.Config):
        name = "tickets"