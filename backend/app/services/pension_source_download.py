"""Backend-only raw source response ownership; no professional intake route."""
from urllib.parse import quote
from fastapi.responses import StreamingResponse
from app.services.m02_storage import M02OwnedReader

class M02DownloadResponse(StreamingResponse):
    def __init__(self, reader: M02OwnedReader, **kwargs):
        self._reader = reader
        super().__init__(self._stream_reader(), **kwargs)

    def _stream_reader(self):
        try:
            while chunk := self._reader.read(1024 * 1024):
                yield chunk
        finally:
            self._reader.close()

    async def __call__(self, scope, receive, send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            self._reader.close()

    def close(self) -> None:
        self._reader.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

def _build_download_response(
    reader: M02OwnedReader, download_filename: str
) -> M02DownloadResponse:
    try:
        encoded_filename = quote(download_filename, safe="")
        return M02DownloadResponse(
            reader,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": (
                    "attachment; filename=\"m02-source\"; "
                    f"filename*=UTF-8''{encoded_filename}"
                ),
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "no-store",
            },
        )
    except BaseException:
        reader.close()
        raise
