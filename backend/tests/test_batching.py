import pytest

from app.common.batching import batched_items


def test_batched_items_empty_input() -> None:
    assert list(batched_items([], 3)) == []


def test_batched_items_exact_batch_size() -> None:
    assert list(batched_items(["a", "b"], 2)) == [("a", "b")]


def test_batched_items_partial_final_batch() -> None:
    assert list(batched_items(["a", "b", "c"], 2)) == [("a", "b"), ("c",)]


def test_batched_items_preserves_order() -> None:
    assert list(batched_items([3, 2, 1, 0], 2)) == [(3, 2), (1, 0)]


@pytest.mark.parametrize("batch_size", [0, -1])
def test_batched_items_rejects_invalid_batch_size(batch_size: int) -> None:
    with pytest.raises(ValueError, match="batch_size must be greater than 0"):
        list(batched_items(["a"], batch_size))


def test_batched_items_supports_generic_items() -> None:
    assert list(batched_items([1, 2, 3], 2)) == [(1, 2), (3,)]
