from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from agent.core import AgentShieldService

app = FastAPI(title="AgentShield API", version="0.1.0")
service = AgentShieldService()


class ChatRequest(BaseModel):
    session_id: str = Field(default="session-1")
    user_id: str = Field(default="user-1")
    role: str = Field(default="user")
    message: str


class ApprovalRequest(BaseModel):
    approval_id: str
    approved: bool


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    return service.process_message(
        session_id=req.session_id,
        user_id=req.user_id,
        role=req.role,
        message=req.message,
    )


@app.post("/approve")
def approve(req: ApprovalRequest) -> dict:
    return service.approve_action(approval_id=req.approval_id, approved=req.approved)


@app.get("/audit/verify")
def verify_audit() -> dict:
    return service.audit_logger.verify_chain()


@app.get("/audit/recent")
def recent_audit(limit: int = 50) -> list[dict]:
    return service.audit_logger.recent_events(limit=limit)

