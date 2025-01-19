import os
import sys
from typing import Dict, List, Optional
import json
from piece_parser import PieceParser
from models import Piece, Action, Trigger
from utils import find_files_by_extension

def extract_flow_examples(flow_json_path: str) -> Dict:
    """Extract examples of piece usage from a flow JSON file."""
    try:
        with open(flow_json_path, 'r', encoding='utf-8') as f:
            flow_data = json.load(f)

        examples = {}
        flow_structure = []
        variable_references = {}

        # First extract flow metadata
        examples['_metadata'] = {
            'name': flow_data.get('name', ''),
            'description': flow_data.get('description', ''),
            'tags': flow_data.get('tags', []),
            'pieces': flow_data.get('pieces', []),
            'template_name': flow_data.get('template', {}).get('displayName', '')
        }

        if 'template' in flow_data and 'trigger' in flow_data['template']:
            current = flow_data['template']['trigger']
            step_number = 0

            # First document the trigger and its outputs
            if current.get('type') == 'WEBHOOK':
                flow_structure.append({
                    'step': 'trigger',
                    'type': 'WEBHOOK',
                    'settings': current.get('settings', {}),
                    'outputs': {
                        'body': '{{trigger.body}}',
                        'headers': '{{trigger.headers}}',
                        'query': '{{trigger.query}}',
                        'url': '{{trigger.url}}'
                    }
                })

            # Then document each action in the flow
            while current and 'nextAction' in current:
                step_number += 1
                current = current['nextAction']
                if current.get('type') == 'PIECE':
                    piece_name = current['settings']['pieceName']
                    action_name = current['settings']['actionName']
                    step_name = current.get('name', f'step_{step_number}')
                    key = f"{piece_name}:{action_name}"

                    # Extract variable references from input
                    input_vars = {}
                    if 'input' in current['settings']:
                        for input_key, input_value in current['settings']['input'].items():
                            if isinstance(input_value, str) and '{{' in input_value:
                                input_vars[input_key] = input_value

                    # Extract error handling options
                    error_handling = current['settings'].get('errorHandlingOptions', {})

                    # Store the example for this specific action
                    examples[key] = {
                        'input': current['settings'].get('input', {}),
                        'pieceVersion': current['settings'].get('pieceVersion'),
                        'settings': current['settings'],
                        'step_number': step_number,
                        'step_name': step_name,
                        'variable_references': input_vars,
                        'error_handling': error_handling,
                        'package_type': current['settings'].get('packageType', 'REGISTRY'),
                        'piece_type': current['settings'].get('pieceType', 'OFFICIAL')
                    }

                    # Document the flow structure
                    flow_structure.append({
                        'step': step_number,
                        'name': step_name,
                        'piece_name': piece_name,
                        'action_name': action_name,
                        'settings': current['settings'],
                        'input_variables': input_vars,
                        'error_handling': error_handling,
                        'package_type': current['settings'].get('packageType', 'REGISTRY'),
                        'piece_type': current['settings'].get('pieceType', 'OFFICIAL')
                    })

                    # Track variable references for documentation
                    if input_vars:
                        variable_references[step_name] = input_vars

        examples['_flow_structure'] = flow_structure
        examples['_variable_references'] = variable_references
        return examples
    except Exception as e:
        print(f"Warning: Could not parse flow example file: {str(e)}")
        return {}

def generate_property_docs(prop) -> List[str]:
    """Generate documentation for a property with enhanced details."""
    doc = []
    requirement = "**Required**" if prop.required else "Optional"
    doc.append(f"- **{prop.display_name}** ({requirement})")
    doc.append(f"  - Type: `{prop.property_type}`")
    if prop.description:
        doc.append(f"  - Description: {prop.description}")
    if prop.default_value is not None:
        doc.append(f"  - Default Value: `{prop.default_value}`")
    if prop.validation_rules:
        doc.append("  - Validation Rules:")
        for rule, value in prop.validation_rules.items():
            doc.append(f"    - {rule}: {value}")
    doc.append("")
    return doc

def generate_variable_reference_docs(component, flow_examples: Dict) -> List[str]:
    """Generate documentation about how to reference variables from this step."""
    doc = []
    if component.piece_name and component.name:
        example_key = f"{component.piece_name}:{component.name}"
        if example_key in flow_examples:
            example = flow_examples[example_key]
            step_name = example.get('step_name', 'step_1')

            # Document input variable references if any
            if example.get('variable_references'):
                doc.append("#### Input Variables Used")
                doc.append("This step uses the following variables from previous steps:")
                for input_key, ref_value in example['variable_references'].items():
                    doc.append(f"- `{input_key}`: {ref_value}")
                doc.append("")

            # Document output variables that can be used in next steps
            doc.append("#### Output Variables")
            doc.append(f"To reference outputs from this step in later steps, use: `{{{{{step_name}}}}}`")
            doc.append("")

            # Show specific output fields if we can determine them
            if 'settings' in example and 'input' in example['settings']:
                doc.append("Available output fields:")
                for field in example['settings']['input'].keys():
                    doc.append(f"- `{{{{{step_name}.{field}}}}}`")
                doc.append("")

            # Special handling for trigger step outputs
            if step_name == 'trigger' and example.get('type') == 'WEBHOOK':
                doc.append("Webhook trigger output fields:")
                doc.append("- `{{trigger.body}}` - The request body")
                doc.append("- `{{trigger.headers}}` - The request headers")
                doc.append("- `{{trigger.query}}` - The query parameters")
                doc.append("- `{{trigger.url}}` - The webhook URL")
                doc.append("")

    return doc

def generate_usage_example(component, flow_examples: Dict) -> List[str]:
    """Generate usage example documentation for an action or trigger."""
    doc = []

    # Check if we have a matching example from the flow
    if component.piece_name and component.name:
        example_key = f"{component.piece_name}:{component.name}"
        if example_key in flow_examples:
            example = flow_examples[example_key]
            doc.append("#### Usage Example")
            doc.append(f"Step {example.get('step_number', '1')} (`{example.get('step_name', 'step_1')}`)")
            doc.append("```json")
            doc.append("{")
            doc.append('  "type": "PIECE",')
            doc.append(f'  "name": "{example.get("step_name", "step_1")}",')
            doc.append('  "settings": {')

            # Show input parameters
            if example['input']:
                doc.append('    "input": {')
                for key, value in example['input'].items():
                    doc.append(f'      "{key}": {json.dumps(value)},')
                doc.append('    },')

            # Show piece version and other settings
            if example['pieceVersion']:
                doc.append(f'    "pieceVersion": "{example["pieceVersion"]}",')

            # Show package type and piece type
            doc.append(f'    "packageType": "{example.get("package_type", "REGISTRY")}",')
            doc.append(f'    "pieceType": "{example.get("piece_type", "OFFICIAL")}",')

            # Show error handling options
            if example.get('error_handling'):
                doc.append('    "errorHandlingOptions": {')
                for opt_name, opt_value in example['error_handling'].items():
                    doc.append(f'      "{opt_name}": {json.dumps(opt_value)},')
                doc.append('    },')

            doc.append(f'    "pieceName": "{component.piece_name}",')
            doc.append(f'    "actionName": "{component.name}"')
            doc.append('  }')
            doc.append("}")
            doc.append("```")
            doc.append("")

            # Add variable reference documentation
            doc.extend(generate_variable_reference_docs(component, flow_examples))

    return doc

def generate_flow_structure_docs(flow_examples: Dict) -> List[str]:
    """Generate documentation about the overall flow structure."""
    doc = []
    if '_flow_structure' in flow_examples:
        doc.append("## Flow Structure Example")

        # Add flow metadata if available
        if '_metadata' in flow_examples:
            metadata = flow_examples['_metadata']
            doc.append("\n### Flow Metadata")
            doc.append("```json")
            doc.append("{")
            doc.append(f'  "name": "{metadata["name"]}",')
            doc.append(f'  "description": "{metadata["description"]}",')
            doc.append('  "tags": [')
            for tag in metadata['tags']:
                doc.append(f'    "{tag}",')
            doc.append('  ],')
            doc.append('  "pieces": [')
            for piece in metadata['pieces']:
                doc.append(f'    "{piece}",')
            doc.append('  ],')
            doc.append(f'  "template": {{')
            doc.append(f'    "displayName": "{metadata["template_name"]}"')
            doc.append('  }')
            doc.append("}")
            doc.append("```\n")

        # Flow overview in natural language
        flow_structure = flow_examples['_flow_structure']
        doc.append("### Flow Overview")
        doc.append("This flow demonstrates the following sequence:")
        for step in flow_structure:
            if step.get('step') == 'trigger':
                doc.append("1. Starts with a webhook trigger")
            else:
                doc.append(f"{step['step'] + 1}. Executes {step['piece_name']} piece with action '{step['action_name']}'")
        doc.append("")

        # Show the complete JSON configuration
        doc.append("### Complete Flow Configuration")
        doc.append("```json")
        doc.append("{")
        doc.append('  "trigger": {')

        for i, step in enumerate(flow_structure):
            indent = '    ' * (i + 1)
            if step.get('step') == 'trigger':
                doc.append('    "type": "WEBHOOK",')
                doc.append('    "settings": {},')
                doc.append('    "nextAction": {')
            else:
                doc.append(f'{indent}"name": "{step["name"]}",')
                doc.append(f'{indent}"type": "PIECE",')
                doc.append(f'{indent}"settings": {{')
                doc.append(f'{indent}  "pieceName": "{step["piece_name"]}",')
                doc.append(f'{indent}  "actionName": "{step["action_name"]}",')
                doc.append(f'{indent}  "packageType": "{step["package_type"]}",')
                doc.append(f'{indent}  "pieceType": "{step["piece_type"]}",')

                # Include error handling options
                if step.get('error_handling'):
                    doc.append(f'{indent}  "errorHandlingOptions": {{')
                    for opt_name, opt_value in step['error_handling'].items():
                        doc.append(f'{indent}    "{opt_name}": {json.dumps(opt_value)},')
                    doc.append(f'{indent}  }},')

                # Include input variables if available
                if step.get('input_variables'):
                    doc.append(f'{indent}  "input": {{')
                    for var_name, var_value in step['input_variables'].items():
                        doc.append(f'{indent}    "{var_name}": "{var_value}",')
                    doc.append(f'{indent}  }}')

                doc.append(f'{indent}}}')
                if i < len(flow_structure) - 1:
                    doc.append(f'{indent},"nextAction": {{')
                else:
                    doc.append(f'{indent}}}')

        # Close all open brackets
        doc.extend(['    }' for _ in range(len(flow_structure)-1)])
        doc.append("  }")
        doc.append("}")
        doc.append("```")

        # Document variable references
        doc.append("\n### Variable References")
        doc.append("The following variables are passed between steps:")

        if '_variable_references' in flow_examples:
            for step_name, vars in flow_examples['_variable_references'].items():
                doc.append(f"\n**Step `{step_name}`**")
                for var_name, var_value in vars.items():
                    doc.append(f"- Uses `{var_value}` for input `{var_name}`")

        doc.append("\n")
    return doc

def generate_documentation(piece: Piece, flow_examples: Dict) -> str:
    """Generate documentation for a piece and its actions."""
    doc = []

    # Piece header with divider
    doc.append(f"# {piece.display_name}")
    if piece.description:
        doc.append(f"\n{piece.description}")
    doc.append(f"\nMinimum Supported Release: {piece.minimum_supported_release}")
    if piece.authors:
        doc.append(f"Authors: {', '.join(piece.authors)}")
    if piece.categories:
        doc.append(f"Categories: {', '.join(piece.categories)}")
    if piece.auth_type:
        doc.append(f"\nAuthentication: {piece.auth_type}")
    doc.append("\n---\n")

    # Add flow structure documentation if available
    doc.extend(generate_flow_structure_docs(flow_examples))

    # Actions documentation
    if piece.actions:
        doc.append("## Actions\n")
        for action in piece.actions:
            doc.append(f"### {action.display_name}")
            if action.description:
                doc.append(f"\n{action.description}\n")

            if action.piece_version:
                doc.append(f"Version: {action.piece_version}\n")

            if action.properties:
                doc.append("#### Parameters\n")
                for prop in action.properties:
                    doc.extend(generate_property_docs(prop))
            else:
                doc.append("This action has no configurable parameters.\n")

            # Add usage example from flow if available
            doc.extend(generate_usage_example(action, flow_examples))
            doc.append("---\n")

    # Triggers documentation
    if piece.triggers:
        doc.append("## Triggers\n")
        for trigger in piece.triggers:
            doc.append(f"### {trigger.display_name}")
            if trigger.description:
                doc.append(f"\n{trigger.description}\n")

            if trigger.piece_version:
                doc.append(f"Version: {trigger.piece_version}\n")

            if trigger.properties:
                doc.append("#### Parameters\n")
                for prop in trigger.properties:
                    doc.extend(generate_property_docs(prop))
            else:
                doc.append("This trigger has no configurable parameters.\n")

            # Add usage example from flow if available
            doc.extend(generate_usage_example(trigger, flow_examples))
            doc.append("---\n")

    if not piece.actions and not piece.triggers:
        doc.append("\nThis piece has no actions or triggers available.")

    # Add final newline
    doc.append("\n")
    return "\n".join(doc)

def process_piece_directory(directory: str, flow_examples: Optional[Dict] = None) -> List[str]:
    """Process a piece directory and generate documentation."""
    parser = PieceParser()
    docs = []

    # Load flow examples if provided
    flow_examples = flow_examples or {}

    # Find index.ts files
    index_files = find_files_by_extension(directory, "index.ts")

    for index_file in index_files:
        if "src" not in index_file:
            continue

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse piece
            piece = parser.parse_piece(content)
            if not piece:
                print(f"Warning: Could not parse piece from {index_file}")
                continue

            base_dir = os.path.dirname(index_file)

            # Find and parse actions
            action_dir = os.path.join(base_dir, "lib", "actions")
            if os.path.exists(action_dir):
                action_files = find_files_by_extension(action_dir, ".ts")

                for action_file in action_files:
                    try:
                        with open(action_file, 'r', encoding='utf-8') as f:
                            action_content = f.read()
                        action = parser.parse_action(action_content)
                        if action:
                            # Set piece-specific information
                            action.piece_name = piece.name
                            piece.actions.append(action)
                    except Exception as e:
                        print(f"Warning: Error parsing action file {action_file}: {str(e)}")

            # Find and parse triggers (check both triggers and trigger directories)
            for trigger_dirname in ["triggers", "trigger"]:
                trigger_dir = os.path.join(base_dir, "lib", trigger_dirname)
                if os.path.exists(trigger_dir):
                    trigger_files = find_files_by_extension(trigger_dir, ".ts")

                    for trigger_file in trigger_files:
                        try:
                            with open(trigger_file, 'r', encoding='utf-8') as f:
                                trigger_content = f.read()
                            trigger = parser.parse_trigger(trigger_content)
                            if trigger:
                                # Set piece-specific information
                                trigger.piece_name = piece.name
                                piece.triggers.append(trigger)
                        except Exception as e:
                            print(f"Warning: Error parsing trigger file {trigger_file}: {str(e)}")

            # Generate documentation with flow examples
            docs.append(generate_documentation(piece, flow_examples))

        except Exception as e:
            print(f"Error processing {index_file}: {str(e)}")

    return docs

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <pieces_directory>")
        sys.exit(1)

    pieces_dir = sys.argv[1]
    if not os.path.exists(pieces_dir):
        print(f"Directory not found: {pieces_dir}")
        sys.exit(1)

    # Use all provided example flow JSONs
    example_flow_paths = [
        "attached_assets/Redundancy Detection Guardrail Agent (1).json",
        "attached_assets/Format and Structure Guardrail Agent (1).json",
        "attached_assets/Social Media Content Generator.json",
        "attached_assets/Calendar Invite Creation Agent.json",
        "attached_assets/Contract Clause Extraction Agent.json",
        "attached_assets/Contract summarization Agent.json",
        "attached_assets/MeetingPrepReport.json",
        "attached_assets/Order Status Update Agent.json",
        "attached_assets/PO Matching Agent.json",
        "attached_assets/Payroll Discrepancy Detection Agent DND.json",
        "attached_assets/SLA Compliance Monitoring Agent.json",
        "attached_assets/Tax Compliance Validation Agent.json",
        "attached_assets/Vendor Data Validation Agent.json"
    ]

    # Combine examples from all flow files
    all_examples: Dict = {}
    for flow_path in example_flow_paths:
        try:
            if os.path.exists(flow_path):
                examples = extract_flow_examples(flow_path)
                for key, value in examples.items():
                    if key not in all_examples:
                        all_examples[key] = value
                    elif key != '_flow_structure' and key != '_variable_references':
                        # Merge examples for the same piece:action combination
                        if isinstance(value, dict) and isinstance(all_examples[key], dict):
                            all_examples[key].update(value)
        except Exception as e:
            print(f"Warning: Error processing flow example {flow_path}: {str(e)}")
            continue

    # Process all pieces and generate documentation
    all_docs = process_piece_directory(pieces_dir, all_examples)

    if not all_docs:
        print("No pieces were found or could be processed.")
        sys.exit(1)

    # Write documentation to file
    output_file = "pieces_documentation.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n\n".join(all_docs))

    print(f"Documentation generated successfully: {output_file}")

if __name__ == "__main__":
    main()