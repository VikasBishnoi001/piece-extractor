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

        # Extract options for Select/MultiSelect
        if "options:" in prop_content:
            options_match = re.search(r'options:\s*(\[.*?\])', prop_content, re.DOTALL)
            if options_match:
                try:
                    # Clean and parse options string
                    options_str = options_match.group(1).replace('\n', '').strip()
                    rules['options'] = options_str
                except:
                    pass

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

    def extract_settings_template(self, example_data: Dict) -> Optional[StepSettings]:
        """Extract settings template from flow example data."""
        if not example_data or not isinstance(example_data, dict):
            return None

        error_handling = ErrorHandlingOptions()
        if 'error_handling' in example_data:
            error_opts = example_data['error_handling']
            error_handling.retry_on_failure = error_opts.get('retryOnFailure', {}).get('value', False)
            error_handling.continue_on_failure = error_opts.get('continueOnFailure', {}).get('value', False)
            error_handling.max_retries = error_opts.get('maxRetries')
            error_handling.retry_interval = error_opts.get('retryInterval')

        return StepSettings(
            piece_name=example_data.get('pieceName', ''),
            piece_version=example_data.get('pieceVersion', '0.0.1'),
            action_name=example_data.get('actionName', ''),
            input=example_data.get('input', {}),
            input_ui_info=example_data.get('inputUiInfo', {}),
            package_type=example_data.get('packageType', 'REGISTRY'),
            error_handling=error_handling
        )

    def parse_property(self, prop_name: str, prop_content: str) -> Optional[Property]:
        """Parse a Property definition from TypeScript code."""
        if not prop_content:
            return None

        display_name = extract_value_by_key(prop_content, "displayName")
        description = extract_value_by_key(prop_content, "description")
        required = "required: true" in prop_content.lower()

        # Extract property type
        type_match = re.search(r'Property\.(\w+)\({', prop_content)
        if not type_match:
            return None

        raw_type = type_match.group(1)
        property_type = self.property_types.get(raw_type, raw_type)

        # Extract additional metadata
        validation_rules = self.extract_validation_rules(prop_content)
        default_value = self.extract_default_value(prop_content)

        # Extract UI info if present
        ui_info_match = re.search(r'inputUiInfo:\s*({[^}]+})', prop_content)
        input_ui_info = None
        if ui_info_match:
            try:
                ui_str = ui_info_match.group(1)
                input_ui_info = eval(ui_str)  # Safe since we control the input
            except:
                pass

        # Extract package type if present
        package_type_match = re.search(r'packageType:\s*[\'"]([^\'"]+)[\'"]', prop_content)
        package_type = package_type_match.group(1) if package_type_match else None

        return Property(
            name=prop_name,
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            required=required,
            property_type=property_type,
            validation_rules=validation_rules,
            default_value=default_value,
            input_ui_info=input_ui_info,
            package_type=package_type
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
        display_name = extract_value_by_key(component_def, "displayName")
        description = extract_value_by_key(component_def, "description")

        # Extract version information if available
        version_match = re.search(r'pieceVersion:\s*[\'"]([^\'"]+)[\'"]', component_def)
        piece_version = version_match.group(1) if version_match else None

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

        # Extract trigger type for triggers
        trigger_type = None
        if component_type == "Trigger":
            type_match = re.search(r'type:\s*(\w+)', component_def)
            if type_match:
                trigger_type = type_match.group(1)

        component_class = Action if component_type == "Action" else Trigger
        return component_class(
            name=clean_typescript_string(name),
            display_name=clean_typescript_string(display_name),
            description=clean_typescript_string(description),
            properties=properties,
            piece_version=piece_version,
            settings_template=None,  # Will be populated later from flow examples
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
        description = extract_value_by_key(piece_def, "description")
        min_release = extract_value_by_key(piece_def, "minimumSupportedRelease")
        logo_url = extract_value_by_key(piece_def, "logoUrl")

        # Extract authors array
        authors_match = re.search(r'authors:\s*\[(.*?)\]', piece_def)
        authors = []
        if authors_match:
            authors_str = authors_match.group(1)
            authors = [
                clean_typescript_string(a.strip())
                for a in re.findall(r'["\']([^"\']+)["\']', authors_str)
            ]

        # Extract categories if present
        categories_match = re.search(r'categories:\s*\[(.*?)\]', piece_def)
        categories = []
        if categories_match:
            categories_str = categories_match.group(1)
            categories = [
                clean_typescript_string(c.strip())
                for c in re.findall(r'["\']([^"\']+)["\']', categories_str)
            ]

        # Extract auth type and settings
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
            description=clean_typescript_string(description),
            minimum_supported_release=clean_typescript_string(min_release),
            logo_url=clean_typescript_string(logo_url),
            actions=[],
            triggers=[],
            authors=authors,
            categories=categories,
            auth_type=auth_type,
            package_type=package_type,
            piece_type=piece_type
        )