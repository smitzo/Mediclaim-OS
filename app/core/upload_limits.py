"""Bound request bodies before the multipart parser; spill bounded data to disk."""
from tempfile import SpooledTemporaryFile
from starlette.responses import JSONResponse
from app.core.config import settings


class RequestSizeLimit:
    def __init__(self, app): self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        try: declared = int(headers.get(b"content-length", b"0"))
        except ValueError: declared = settings.max_request_bytes+1
        if declared < 0 or declared > settings.max_request_bytes:
            return await JSONResponse({"detail": "Request body exceeds the configured limit."}, status_code=413)(scope, receive, send)
        with SpooledTemporaryFile(max_size=1024*1024) as body:
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect": return
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > settings.max_request_bytes:
                    return await JSONResponse({"detail": "Request body exceeds the configured limit."}, status_code=413)(scope, receive, send)
                body.write(chunk)
                if not message.get("more_body", False): break
            body.seek(0)
            finished = False
            async def replay():
                nonlocal finished
                if finished: return await receive()
                chunk = body.read(64*1024)
                finished = body.tell() == total
                return {"type": "http.request", "body": chunk, "more_body": not finished}
            await self.app(scope, replay, send)
