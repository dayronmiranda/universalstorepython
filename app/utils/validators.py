"""Custom validators"""

from bson import ObjectId
from bson.errors import InvalidId


def validate_object_id(id_str: str) -> bool:
    """
    Validate if a string is a valid MongoDB ObjectId

    Args:
        id_str: String to validate

    Returns:
        True if valid ObjectId, False otherwise
    """
    try:
        ObjectId(id_str)
        return True
    except (InvalidId, TypeError):
        return False
