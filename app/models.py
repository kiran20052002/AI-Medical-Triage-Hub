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
    role: str = 'patient'
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "patients"


class Doctor(Document):
    email: EmailStr
    password: str
    role: str = 'doctor'
    specialist: List[str] = []
    created_at: datetime = Field(default_factory=datetime.now)

    class Settings(BaseConfig.Config):
        name = "doctors"



