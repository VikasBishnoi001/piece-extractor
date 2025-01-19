import os
import re
from typing import List, Dict, Optional, Any

def clean_typescript_string(value: str) -> str:
    """Clean TypeScript string by removing quotes and escapes while preserving formatting."""
    if not value:
        return ""
    # Remove quotes at the start and end
    value = value.strip("'\"`)")
    # Handle escaped quotes and characters
    value = value.replace("\\'", "'").replace('\\"', '"').replace('\\n', ' ')
    # Handle newlines and excessive spaces while preserving sentence structure
    value = re.sub(r'\s+', ' ', value).strip()
    return value

def extract_object_properties(content: str, start_marker: str = "{", end_marker: str = "}") -> str:
    """Extract object properties between markers with improved TypeScript handling."""
    if not content:
        return ""

    start_idx = content.find(start_marker)
    if start_idx == -1:
        return ""

    count = 1
    current_idx = start_idx + 1
    in_string = False
    string_char = None
    in_template = False

    while count > 0 and current_idx < len(content):
        char = content[current_idx]

        # Handle string literals and template literals
        if char == '`':
            if not in_string:
                in_template = not in_template
        elif char in "'\"" and content[current_idx - 1] != '\\':
            if not in_template:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
        elif not in_string and not in_template:
            if char == start_marker:
                count += 1
            elif char == end_marker:
                count -= 1

        current_idx += 1

    return content[start_idx:current_idx] if count == 0 else ""

def extract_value_by_key(content: str, key: str) -> str:
    """Extract value for a specific key from TypeScript object with improved formatting."""
    if not content or not key:
        return ""

    patterns = [
        # Multi-line template literals with optional spaces and newlines
        rf'{key}:\s*`([\s\S]*?)`(?=\s*[,\n}}])',
        # Multi-line string with double quotes
        rf'{key}:\s*"([\s\S]*?)"(?=\s*[,\n}}])',
        # Multi-line string with single quotes
        rf"{key}:\s*'([\s\S]*?)'(?=\s*[,\n}}])",
        # Array values
        rf'{key}:\s*\[([\s\S]*?)\](?=\s*[,\n}}])',
        # Single line with any quote style and optional trailing comma
        rf'{key}:\s*[\'"`](.*?)[\'"`](?=\s*[,\n}}])'
    ]

    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # For array values, clean up the formatting
            if pattern.endswith('\]'):
                value = value.replace('\n', '').replace('  ', ' ')
            # Clean up the value while preserving meaningful whitespace
            # Split on newlines, strip each line, and rejoin with spaces
            cleaned_value = ' '.join(
                line.strip() 
                for line in value.split('\n') 
                if line.strip()
            )
            return cleaned_value

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