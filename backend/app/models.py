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
    ticket_id: PydanticObjectId = Field(alias="ticketId")
    content: dict
    formatted_report: Optional[str] = Field(default=None, alias="formattedReport")
    embedding: List[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "reports"

class MedicalDocumentParent(Document):
    title: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "medical_document_parents"

class MedicalDocumentChunk(Document):
    parent_id: PydanticObjectId = Field(alias="parentId")
    content: str
    embedding: List[float] = Field(default_factory=list)

    class Settings(BaseConfig.Config):
        name = "medical_document_chunks"

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

class RefreshToken(Document):
    token: str
    user_id: PydanticObjectId = Field(alias="userId")
    user_role: str = Field(alias="userRole")
    expires_at: datetime = Field(alias="expiresAt")
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

    class Settings(BaseConfig.Config):
        name = "refresh_tokens"

class ChatMessage(Document):
    ticket_id: PydanticObjectId = Field(alias="ticketId")
    sender_id: PydanticObjectId = Field(alias="senderId")
    sender_name: str = Field(alias="senderName")
    sender_role: str = Field(alias="senderRole")
    text: str
    created_at: datetime = Field(default_factory=datetime.now, alias="createdAt")

    class Settings(BaseConfig.Config):
        name = "chat_messages"