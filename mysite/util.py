"""
Utilities
"""
def to_bytes(data) -> bytes:
    if isinstance(data, str):
        return data.encode("UTF-8")
    elif isinstance(data, bytes):
        return data
    else:
        return b"".join([to_bytes(chunk) for chunk in iter(data)])