"""Local API request limits and browser-origin protection."""

from starlette.responses import JSONResponse


MAX_REQUEST_BYTES = 4 * 1024 * 1024
ALLOWED_BROWSER_ORIGINS = {"http://127.0.0.1:5173"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class LocalRequestGuard:
    """Bound request bodies and reject browser writes from other origins."""

    def __init__(self, app, allowed_origins=None):
        self.app = app
        self.allowed_origins = frozenset(ALLOWED_BROWSER_ORIGINS if allowed_origins is None else allowed_origins)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        origin = headers.get(b"origin", b"").decode("latin-1")
        if scope["method"] in WRITE_METHODS and origin and origin not in self.allowed_origins:
            return await JSONResponse({"detail": "Browser origin is not allowed."}, status_code=403)(scope, receive, send)

        body = bytearray()
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            if event["type"] != "http.request":
                continue
            body.extend(event.get("body", b""))
            if len(body) > MAX_REQUEST_BYTES:
                return await JSONResponse({"detail": "Request body is too large."}, status_code=413)(scope, receive, send)
            if not event.get("more_body", False):
                break

        async def replay():
            nonlocal body
            if body is not None:
                result = bytes(body)
                body = None
                return {"type": "http.request", "body": result, "more_body": False}
            return await receive()

        async def secure_send(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"cache-control", b"no-store"),
                ])
            await send(message)

        await self.app(scope, replay, secure_send)
