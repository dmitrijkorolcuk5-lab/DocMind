from collections.abc import Iterator, Sequence
from itertools import batched


def batched_items[T](items: Sequence[T], batch_size: int) -> Iterator[tuple[T, ...]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")
    return batched(items, batch_size)
