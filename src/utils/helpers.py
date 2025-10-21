from typing import Iterable


def chunk_iterable(items: Iterable, chunk_size: int):
    """Yield successive chunks from an iterable."""
    chunk = []
    for item in items:
        chunk.append(item)
        if len(chunk) == chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


