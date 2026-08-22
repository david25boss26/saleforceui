import hashlib

def calculate_file_hash(filepath: str) -> str:
    """Calculates the MD5 hash of a file to check for duplicate uploads."""
    hasher = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def calculate_row_hash(row_data: dict, keys: list) -> str:
    """Generates an idempotency hash for a single record based on specified keys."""
    # Order keys for consistency
    ordered_keys = sorted(keys)
    vals = [str(row_data.get(k, "")).strip().lower() for k in ordered_keys]
    raw_str = "|".join(vals)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()
