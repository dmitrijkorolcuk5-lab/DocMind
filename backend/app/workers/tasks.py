from datetime import UTC, datetime


async def health_job(ctx: dict[str, object]) -> dict[str, str]:
    """Small executable job used to verify the worker/Redis path."""
    del ctx
    return {"status": "ok", "timestamp": datetime.now(UTC).isoformat()}


# The process_document(document_id) job is intentionally deferred. Its future contract is:
# transition uploaded -> processing, parse, chunk, embed, persist atomically, then mark ready;
# failures must mark the document failed and retain a safe diagnostic message.

