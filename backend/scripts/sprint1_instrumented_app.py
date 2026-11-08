"""Disposable acceptance ASGI wrapper. Never used by product deployment."""

import contextvars
import os
from sqlalchemy import event
from app.db.session import engine
from app.main import app as application

assert os.environ.get("OPSCONTROL_V16_ACCEPTANCE") == "1"
assert os.environ.get("ENVIRONMENT") == "test"
queries = contextvars.ContextVar("sprint_query_count", default=None)


@event.listens_for(engine, "before_cursor_execute")
def count_query(*args):
    counter = queries.get()
    if counter is not None:
        counter[0] += 1


async def app(scope, receive, send):
    if scope["type"] != "http":
        return await application(scope, receive, send)
    counter = [0]
    reset = queries.set(counter)

    async def measured_send(message):
        if message["type"] == "http.response.start":
            message = {
                **message,
                "headers": [
                    *message.get("headers", []),
                    (b"x-sprint-test-sql-count", str(counter[0]).encode()),
                ],
            }
        await send(message)

    try:
        await application(scope, receive, measured_send)
    finally:
        queries.reset(reset)
