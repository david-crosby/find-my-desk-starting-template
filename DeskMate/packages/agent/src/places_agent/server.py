import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_agent

app = FastAPI(title="DeskMate Agent", version="0.1.0")

_sessions: dict[str, list[dict]] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str
    user_id: int


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    history = _sessions.setdefault(req.session_id, [])
    reply = run_agent(req.message, history)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    return ChatResponse(reply=reply)


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict:
    _sessions.pop(session_id, None)
    return {"cleared": session_id}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def run() -> None:
    uvicorn.run("places_agent.server:app", host="0.0.0.0", port=8001, reload=True)
