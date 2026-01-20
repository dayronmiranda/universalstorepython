"""Pagination utilities"""

from typing import List, Any
from math import ceil


def paginate(items: List[Any], page: int = 1, limit: int = 20) -> dict:
    """
    Paginate a list of items

    Args:
        items: List of items to paginate
        page: Current page number (1-indexed)
        limit: Number of items per page

    Returns:
        Dictionary with pagination data
    """
    total = len(items)
    pages = ceil(total / limit) if total > 0 else 1

    start = (page - 1) * limit
    end = start + limit

    return {
        "data": items[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }
