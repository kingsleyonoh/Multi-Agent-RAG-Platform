import httpx
import json

resp = httpx.post(
    "http://127.0.0.1:8000/api/search",
    headers={"X-API-Key": "dev-key-1", "X-User-Id": "test-user"},
    json={"query": "What is Python?", "threshold": 0.1, "top_k": 5}
)

with open("error.json", "w") as f:
    json.dump(resp.json(), f, indent=2)
