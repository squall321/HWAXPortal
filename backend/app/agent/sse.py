"""SSE framing helpers — the portal's first streaming surface.

Frames follow the §5 contract: event: <name>\\ndata: <json>\\n\\n. Kept tiny and
dependency-free (no sse-starlette) so StreamingResponse can emit these directly.
"""

import json
from typing import Any


def sse_event(event: str, data: dict[str, Any]) -> bytes:
    """One SSE frame. data is JSON-encoded on a single `data:` line."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode()
