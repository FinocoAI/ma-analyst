import hashlib


def transcript_key(ticker: str, quarter: str) -> str:
    return f"transcript:{ticker}:{quarter}"


def signal_key(ticker: str, quarter: str, target_profile_hash: str) -> str:
    return f"signal:{ticker}:{quarter}:{target_profile_hash}"


def profile_hash(profile_json: str) -> str:
    """Generate a short hash of the target profile for cache keying."""
    return hashlib.md5(profile_json.encode()).hexdigest()[:12]


def prospect_key(target_profile_hash: str, filters_hash: str) -> str:
    return f"prospects:{target_profile_hash}:{filters_hash}"
