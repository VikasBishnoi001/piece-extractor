import re
from typing import List, Dict, Optional
from models import Piece, Action, Trigger, Property
from utils import clean_typescript_string, extract_object_properties, extract_value_by_key

class PieceParser:
    def __init__(self):
        self.property_types = {
            'ShortText': 'Text',
            'LongText': 'Text',
            'Number': 'Number',
            'Checkbox': 'Boolean',
            'Select': 'Select',
            'MultiSelect': 'MultiSelect',
            'File': 'File',
            'Json': 'JSON',
            'DateTime': 'DateTime',
            'Dictionary': 'Dictionary'
        }

    def parse_property(self, prop_name: str, prop_content: str) -> Optional[Property]:
        """Parse a Property definition from TypeScript code."""
        if not prop_content:
            return None

        display_name = extract_value_by_key(prop_content, "displayName")
        description = extract_value_by_key(prop_content, "description")
        required = "required: true" in prop_content

        # Extract property type using improved pattern
        type_match = re.search(r'Property\.(\w+)\({', prop_content)
        if not type_match:
            return None

        raw_type = type_match.group(1)
        property_type = self.property_types.get(raw_type, raw_type)

        return Property(
            name=prop_name,
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            required=required,
            property_type=property_type
        )

    def parse_component(self, content: str, component_type: str) -> Optional[Action | Trigger]:
        """Parse an Action or Trigger definition from TypeScript code."""
        create_fn = f"create{component_type}"
        if create_fn not in content:
            return None

        # Extract the entire component definition
        start_idx = content.find(f"{create_fn}({{")
        if start_idx == -1:
            return None

        component_def = extract_object_properties(content[start_idx + len(create_fn) + 1:])
        if not component_def:
            return None

        name = extract_value_by_key(component_def, "name")
        display_name = extract_value_by_key(component_def, "displayName")
        description = extract_value_by_key(component_def, "description")

        # Extract properties section
        props_start = component_def.find("props:")
        properties = []

        if props_start != -1:
            props_str = component_def[props_start:]
            props_obj = extract_object_properties(props_str)
            if props_obj:
                # Process each property block between the root-level braces
                prop_content = props_obj[1:-1]  # Remove outer braces
                while prop_content:
                    # Find the next property name
                    prop_match = re.search(r'^\s*(\w+):\s*Property\.', prop_content)
                    if not prop_match:
                        break

                    prop_name = prop_match.group(1)
                    prop_start = prop_match.start()

                    # Find the start of the next property or end of content
                    next_prop = re.search(r'\n\s*\w+:\s*Property\.', prop_content[prop_start + 1:])
                    if next_prop:
                        prop_end = prop_start + 1 + next_prop.start()
                        current_prop = prop_content[prop_start:prop_end]
                        prop_content = prop_content[prop_end:]
                    else:
                        current_prop = prop_content[prop_start:]
                        prop_content = ""

                    # Parse the property
                    prop = self.parse_property(prop_name, current_prop)
                    if prop:
                        properties.append(prop)

        component_class = Action if component_type == "Action" else Trigger
        return component_class(
            name=clean_typescript_string(name),
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            properties=properties
        )

    def parse_action(self, content: str) -> Optional[Action]:
        """Parse an Action definition from TypeScript code."""
        return self.parse_component(content, "Action")

    def parse_trigger(self, content: str) -> Optional[Trigger]:
        """Parse a Trigger definition from TypeScript code."""
        return self.parse_component(content, "Trigger")

    def parse_piece(self, content: str) -> Optional[Piece]:
        """Parse a Piece definition from TypeScript code."""
        if "createPiece" not in content:
            return None

        piece_start = content.find("createPiece({")
        if piece_start == -1:
            return None

        piece_def = extract_object_properties(content[piece_start + 11:])
        if not piece_def:
            return None

        display_name = extract_value_by_key(piece_def, "displayName")
        description = extract_value_by_key(piece_def, "description")
        min_release = extract_value_by_key(piece_def, "minimumSupportedRelease")
        logo_url = extract_value_by_key(piece_def, "logoUrl")

        # Extract authors array
        authors_match = re.search(r'authors:\s*\[(.*?)\]', piece_def)
        authors = []
        if authors_match:
            authors_str = authors_match.group(1)
            # Handle quoted strings in array
            authors = [
                clean_typescript_string(a.strip())
                for a in re.findall(r'["\']([^"\']+)["\']', authors_str)
            ]

        return Piece(
            name=clean_typescript_string(display_name).lower().replace(" ", "-"),
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            minimum_supported_release=clean_typescript_string(min_release),
            logo_url=clean_typescript_string(logo_url),
            actions=[],  # Actions will be added separately
            triggers=[],  # Triggers will be added separately
            authors=authors
        )