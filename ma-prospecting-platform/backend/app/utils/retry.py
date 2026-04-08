import asyncio
import logging
from functools import wraps
from typing import TypeVar, Callable

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for exponential backoff retry on async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            raise last_exception
        return wrapper
    return decorator
