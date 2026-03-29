import httpx
import json

resp = httpx.post(
    "http://127.0.0.1:8000/api/chat/sync",
    headers={"X-API-Key": "dev-key-1", "X-User-Id": "test-user"},
    json={
        "query": "What databases are used in this RAG platform?",
        "stream": False
    },
    timeout=60.0
)

with open("chat_response.json", "w") as f:
    try:
        json.dump(resp.json(), f, indent=2)
    except Exception:
        f.write(resp.text)
