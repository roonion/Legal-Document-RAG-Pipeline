"""Locust load testing for RAG API."""

import json

from locust import HttpUser, between, task


class RAGUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def health(self) -> None:
        self.client.get("/health/live", catch_response=True)

    @task(3)
    def chat_query(self) -> None:
        payload = {
            "messages": [{"role": "user", "content": "What is a contract?"}],
            "stream": True,
        }
        with self.client.post(
            "/api/v1/chat",
            json=payload,
            headers={"Accept": "text/event-stream"},
            catch_response=True,
            stream=True,
            name="/api/v1/chat",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"status {resp.status_code}")
                return
            buf = b""
            for chunk in resp.iter_content(chunk_size=4096):
                if not chunk:
                    break
                buf += chunk
                if len(buf) > 8000:
                    break
            if b"text-delta" not in buf and b"data:" not in buf:
                try:
                    data = json.loads(resp.text)
                    if "detail" in data:
                        resp.failure(data["detail"])
                except Exception:
                    resp.failure("empty stream")
