"""
Operations Package
Simple imports for email and file operations
"""

from . import file_operations as file_functions

# Export the tools lists
from .file_operations import LANGCHAIN_TOOLS as FILE_TOOLS

# Combined tools list
ALL_TOOLS =  FILE_TOOLS


__all__ = [
    'file_functions',
    'FILE_TOOLS',
]