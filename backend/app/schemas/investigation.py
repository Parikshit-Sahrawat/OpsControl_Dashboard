from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.entities import InvestigationStatus
class TransitionCreate(BaseModel):
    new_status: InvestigationStatus
    operator: str
    comment: str | None = None
class TransitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    previous_status: InvestigationStatus
    new_status: InvestigationStatus
    operator: str
    comment: str | None
    timestamp: datetime
class NoteCreate(BaseModel):
    operator: str
    text: str
    evidence_reference: str | None = None
class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    operator: str
    text: str
    evidence_reference: str | None
    timestamp: datetime
class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    history_id: UUID
    status: InvestigationStatus
    operator: str | None
    started_at: datetime | None
    resolved_at: datetime | None
    failure_category: str | None
    suspected_cause: str | None
    confidence: str | None
    root_cause: str | None
    root_cause_status: str | None
    transitions: list[TransitionOut]
    notes: list[NoteOut]
