from dataclasses import dataclass
from uuid import UUID

from app.documents.parsers import ParsedBlock, ParsedDocument


@dataclass(frozen=True, slots=True)
class DocumentChunkCandidate:
    document_id: UUID
    content: str
    chunk_index: int
    page_start: int | None
    page_end: int | None
    section_title: str | None
    token_count: int
    metadata: dict[str, object]


def approximate_token_count(text: str) -> int:
    words = text.split()
    if not words:
        return 0
    return max(1, int(len(words) * 1.3))


def _tail_overlap(blocks: list[ParsedBlock], overlap_tokens: int) -> list[ParsedBlock]:
    if overlap_tokens <= 0:
        return []
    selected: list[ParsedBlock] = []
    total = 0
    for block in reversed(blocks):
        selected.insert(0, block)
        total += approximate_token_count(block.text)
        if total >= overlap_tokens:
            break
    return selected


class DocumentChunker:
    def __init__(self, target_tokens: int, overlap_tokens: int) -> None:
        self._target_tokens = target_tokens
        self._overlap_tokens = overlap_tokens

    def chunk(self, document_id: UUID, parsed: ParsedDocument) -> list[DocumentChunkCandidate]:
        chunks: list[DocumentChunkCandidate] = []
        current: list[ParsedBlock] = []
        current_tokens = 0

        for block in parsed.blocks:
            block_tokens = approximate_token_count(block.text)
            if current and current_tokens + block_tokens > self._target_tokens:
                chunks.append(self._build_candidate(document_id, chunks, current))
                current = _tail_overlap(current, self._overlap_tokens)
                current_tokens = sum(approximate_token_count(item.text) for item in current)
            current.append(block)
            current_tokens += block_tokens

        if current:
            chunks.append(self._build_candidate(document_id, chunks, current))
        return chunks

    def _build_candidate(
        self, document_id: UUID, existing: list[DocumentChunkCandidate], blocks: list[ParsedBlock]
    ) -> DocumentChunkCandidate:
        content = "\n\n".join(block.text for block in blocks).strip()
        pages = [block.page_number for block in blocks if block.page_number is not None]
        section_title = next((block.section_title for block in blocks if block.section_title), None)
        return DocumentChunkCandidate(
            document_id=document_id,
            content=content,
            chunk_index=len(existing),
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            section_title=section_title,
            token_count=approximate_token_count(content),
            metadata={
                "block_start": blocks[0].order_index,
                "block_end": blocks[-1].order_index,
                "token_counter": "approximate_word_based",
            },
        )
