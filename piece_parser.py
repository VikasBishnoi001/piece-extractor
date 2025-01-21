import re
from typing import List, Dict, Optional, Union, Any
from models import Piece, Action, Trigger, Property, StepSettings, ErrorHandlingOptions
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

    def extract_validation_rules(self, prop_content: str) -> Optional[Dict]:
        """Extract validation rules from property content."""
        rules = {}

        # Extract min/max values for numbers
        if "min:" in prop_content:
            min_match = re.search(r'min:\s*(\d+)', prop_content)
            if min_match:
                rules['minimum'] = min_match.group(1)

        if "max:" in prop_content:
            max_match = re.search(r'max:\s*(\d+)', prop_content)
            if max_match:
                rules['maximum'] = max_match.group(1)

        # Extract validation function if present
        if "validate:" in prop_content:
            rules['has_validation'] = True

        # Extract options for StaticDropdown/Select/Enum
        options_str = ""
        if any(pattern in prop_content for pattern in ["StaticDropdown", "Select", "options:", "enum:"]):
            # Try first for StaticDropdown/Select format
            options_match = re.search(r'options:\s*{[^}]*options:\s*(\[.*?\])', prop_content, re.DOTALL)
            if options_match:
                try:
                    options_list = []
                    label_values = re.finditer(r'{[^}]*label:\s*[\'"]([^\'"]*)[\'"][^}]*value:\s*([^,}\s]+)', options_match.group(1))
                    for match in label_values:
                        label, value = match.groups()
                        options_list.append(f"{label}: {value}")
                    if options_list:
                        options_str = "\n    " + "\n    ".join(options_list)
                except:
                    pass

            # If no options found, try enum format
            if not options_str:
                enum_match = re.search(r'enum:\s*{([^}]+)}', prop_content)
                if enum_match:
                    try:
                        enum_content = enum_match.group(1)
                        enum_pairs = re.finditer(r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]', enum_content)
                        options_list = [f"{key}: {value}" for key, value in [pair.groups() for pair in enum_pairs]]
                        if options_list:
                            options_str = "\n    " + "\n    ".join(options_list)
                    except:
                        pass

            if options_str:
                rules['options'] = options_str

        return rules if rules else None

    def extract_default_value(self, prop_content: str) -> Optional[Any]:
        """Extract default value from property content."""
        default_match = re.search(r'defaultValue:\s*([^,}\s]+)', prop_content)
        if default_match:
            value = default_match.group(1)
            # Convert to appropriate type
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
            elif value.replace('.','').isdigit():
                return float(value) if '.' in value else int(value)
            return value
        return None

    def parse_property(self, prop_name: str, prop_content: str) -> Optional[Property]:
        """Parse a Property definition from TypeScript code."""
        if not prop_content:
            return None

        display_name = extract_value_by_key(prop_content, "displayName") or prop_name
        description = extract_value_by_key(prop_content, "description")
        required = "required: true" in prop_content.lower()

        type_match = re.search(r'Property\.(\w+)\({', prop_content)
        if not type_match:
            return None

        raw_type = type_match.group(1)
        property_type = self.property_types.get(raw_type, raw_type)

        validation_rules = self.extract_validation_rules(prop_content)
        default_value = self.extract_default_value(prop_content)

        return Property(
            name=prop_name,
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            required=required,
            property_type=property_type,
            validation_rules=validation_rules,
            default_value=default_value,
            input_ui_info=None,
            package_type="REGISTRY"
        )

    def parse_component(self, content: str, component_type: str) -> Optional[Union[Action, Trigger]]:
        """Parse an Action or Trigger definition from TypeScript code."""
        create_fn = f"create{component_type}"
        if create_fn not in content:
            return None

        start_idx = content.find(f"{create_fn}({{")
        if start_idx == -1:
            return None

        component_def = extract_object_properties(content[start_idx + len(create_fn) + 1:])
        if not component_def:
            return None

        name = extract_value_by_key(component_def, "name")
        if not name:  # Skip if no name found
            return None

        display_name = extract_value_by_key(component_def, "displayName")
        description = extract_value_by_key(component_def, "description")

        # Extract properties
        props_start = component_def.find("props:")
        properties = []

        if props_start != -1:
            props_str = component_def[props_start:]
            props_obj = extract_object_properties(props_str)
            if props_obj:
                prop_content = props_obj[1:-1]  # Remove outer braces
                while prop_content:
                    prop_match = re.search(r'^\s*(\w+):\s*Property\.', prop_content)
                    if not prop_match:
                        break

                    prop_name = prop_match.group(1)
                    prop_start = prop_match.start()

                    next_prop = re.search(r'\n\s*\w+:\s*Property\.', prop_content[prop_start + 1:])
                    if next_prop:
                        prop_end = prop_start + 1 + next_prop.start()
                        current_prop = prop_content[prop_start:prop_end]
                        prop_content = prop_content[prop_end:]
                    else:
                        current_prop = prop_content[prop_start:]
                        prop_content = ""

                    prop = self.parse_property(prop_name, current_prop)
                    if prop:
                        properties.append(prop)

        # Extract trigger type and ensure it's always a string
        trigger_type = "PIECE_TRIGGER"  # Default type
        if component_type == "Trigger":
            type_match = re.search(r'type:\s*TriggerStrategy\.(\w+)', component_def)
            if type_match:
                trigger_type = type_match.group(1)
            else:
                type_match = re.search(r'triggerType:\s*[\'"](\w+)[\'"]', component_def)
                if type_match:
                    trigger_type = type_match.group(1)

        component_class = Action if component_type == "Action" else Trigger
        return component_class(
            name=clean_typescript_string(name),
            display_name=clean_typescript_string(display_name or name),
            description=clean_typescript_string(description or ""),
            properties=properties,
            piece_version="0.0.1",  # Default version
            settings_template=None,  # Will be populated from flow examples
            trigger_type=trigger_type if component_type == "Trigger" else None,
            valid=True
        )

    def parse_action(self, content: str) -> Optional[Action]:
        """Parse an Action definition from TypeScript code."""
        result = self.parse_component(content, "Action")
        return result if isinstance(result, Action) else None

    def parse_trigger(self, content: str) -> Optional[Trigger]:
        """Parse a Trigger definition from TypeScript code."""
        result = self.parse_component(content, "Trigger")
        return result if isinstance(result, Trigger) else None

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
        if not display_name:  # Skip if no display name found
            return None

        description = extract_value_by_key(piece_def, "description")
        logo_url = extract_value_by_key(piece_def, "logoUrl")

        # Extract auth type
        auth_type = None
        if "PieceAuth." in piece_def:
            auth_match = re.search(r'PieceAuth\.(\w+)', piece_def)
            if auth_match:
                auth_type = auth_match.group(1)

        # Extract piece type and package type
        piece_type = "OFFICIAL"  # Default value
        package_type = "REGISTRY"  # Default value

        piece_type_match = re.search(r'pieceType:\s*[\'"]([^\'"]+)[\'"]', piece_def)
        if piece_type_match:
            piece_type = piece_type_match.group(1)

        package_type_match = re.search(r'packageType:\s*[\'"]([^\'"]+)[\'"]', piece_def)
        if package_type_match:
            package_type = package_type_match.group(1)

        return Piece(
            name=clean_typescript_string(display_name).lower().replace(" ", "-"),
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description or ""),
            minimum_supported_release="0.0.1",  # Fixed version as requested
            logo_url=clean_typescript_string(logo_url or ""),
            actions=[],
            triggers=[],
            categories=[],  # Removed as requested
            auth_type=auth_type,
            package_type=package_type,
            piece_type=piece_type
        )