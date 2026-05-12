from datetime import date

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from .agent import run_agent

app = FastAPI(title="DeskMate Agent", version="0.1.0")

# In-memory session store: session_id -> list of message dicts.
_sessions: dict[str, list[dict]] = {}
# Per-session auth tokens so tool calls can forward them to the backend.
_session_tokens: dict[str, str] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: int
    user_display_name: str = "User"


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """Send a message to the DeskMate agent and receive a reply.

    A context header is injected into the first message of each new session so
    the agent knows who it is speaking to and what today's date is.
    """
    history = _sessions.setdefault(req.session_id, [])

    # Extract and persist the Bearer token so tool calls can forward it to the backend.
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""
    if token:
        _session_tokens[req.session_id] = token
    session_token = _session_tokens.get(req.session_id, "")

    today = date.today().isoformat()
    user_context = (
        f"User ID: {req.user_id}, "
        f"Name: {req.user_display_name}, "
        f"Today's date: {today}"
    )

    reply = run_agent(req.message, history, user_context=user_context, auth_token=session_token)

    # Append the raw user message (without context header) and the reply so the
    # history shown in the UI matches what the user actually typed.
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})

    return ChatResponse(reply=reply, session_id=req.session_id)


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict:
    """Clear the conversation history for a session."""
    _sessions.pop(session_id, None)
    _session_tokens.pop(session_id, None)
    return {"cleared": session_id}


@app.get("/sessions/{session_id}/history")
def get_history(session_id: str) -> list[dict]:
    """Return the conversation history for a session (role + content pairs)."""
    history = _sessions.get(session_id)
    if history is None:
        raise HTTPException(404, "Session not found")
    return [{"role": m["role"], "content": m["content"]} for m in history]


@app.get("/health")
def health() -> dict:
    """Return a simple liveness check."""
    return {"status": "ok"}


def run() -> None:
    uvicorn.run("places_agent.server:app", host="0.0.0.0", port=8001, reload=True)
