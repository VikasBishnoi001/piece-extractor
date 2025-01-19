import os
import re
from typing import List, Dict, Optional, Any

def clean_typescript_string(value: str) -> str:
    """Clean TypeScript string by removing quotes and escapes."""
    if not value:
        return ""
    return value.strip("'\"").replace("\\'", "'").replace('\\"', '"')

def extract_object_properties(content: str, start_marker: str = "{", end_marker: str = "}") -> str:
    """Extract object properties between markers with improved TypeScript handling."""
    if not content:
        return ""

    start_idx = content.find(start_marker)
    if start_idx == -1:
        return ""

    count = 1
    current_idx = start_idx + 1

    while count > 0 and current_idx < len(content):
        char = content[current_idx]
        # Handle string literals to avoid counting braces inside strings
        if char in "'\"":
            quote = char
            current_idx += 1
            while current_idx < len(content) and content[current_idx] != quote:
                if content[current_idx] == '\\':
                    current_idx += 2  # Skip escaped character
                else:
                    current_idx += 1
        elif char == start_marker:
            count += 1
        elif char == end_marker:
            count -= 1
        current_idx += 1

    return content[start_idx:current_idx] if count == 0 else ""

def extract_value_by_key(content: str, key: str) -> str:
    """Extract value for a specific key from TypeScript object with improved handling."""
    if not content or not key:
        return ""

    # Handle both string and array values
    string_pattern = rf"{key}:\s*['\"]([^'\"]+)['\"]"
    array_pattern = rf"{key}:\s*\[(.*?)\]"

    string_match = re.search(string_pattern, content)
    if string_match:
        return string_match.group(1)

    array_match = re.search(array_pattern, content)
    if array_match:
        return array_match.group(1)

    return ""

def find_files_by_extension(directory: str, extension: str) -> List[str]:
    """Find all files with specific extension in directory and subdirectories."""
    if not os.path.exists(directory):
        return []

    matches = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extension):
                matches.append(os.path.join(root, filename))
    return matches