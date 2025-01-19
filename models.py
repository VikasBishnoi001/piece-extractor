from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class ErrorHandlingOptions:
    retry_on_failure: bool = False
    continue_on_failure: bool = False
    max_retries: Optional[int] = None
    retry_interval: Optional[int] = None

@dataclass
class Property:
    name: str
    display_name: str
    description: str
    required: bool
    property_type: str
    input_ui_info: Optional[Dict] = None  # Store UI-specific information
    default_value: Optional[Any] = None   # Store default values if specified
    validation_rules: Optional[Dict] = None  # Store any validation rules
    package_type: Optional[str] = None    # REGISTRY or ARCHIVE

@dataclass
class StepSettings:
    piece_name: str
    piece_version: str
    action_name: str
    input: Dict[str, Any]
    input_ui_info: Dict[str, Any]
    package_type: str  # REGISTRY or ARCHIVE
    error_handling: ErrorHandlingOptions

@dataclass
class Action:
    name: str
    display_name: str
    description: str
    properties: List[Property]
    piece_name: Optional[str] = None  # The name of the piece this action belongs to
    piece_version: Optional[str] = None  # Version information
    settings_template: Optional[StepSettings] = None  # Example settings from flows
    valid: bool = True
    error_handling: Optional[ErrorHandlingOptions] = None

@dataclass
class Trigger:
    name: str
    display_name: str
    description: str
    properties: List[Property]
    piece_name: Optional[str] = None
    piece_version: Optional[str] = None
    settings_template: Optional[StepSettings] = None
    trigger_type: str = "PIECE_TRIGGER"  # or WEBHOOK, etc.
    valid: bool = True

@dataclass
class Piece:
    name: str
    display_name: str
    description: str
    minimum_supported_release: str
    logo_url: str
    actions: List[Action]
    triggers: List[Trigger]
    authors: List[str]
    categories: List[str] = field(default_factory=list)  # Initialize as empty list
    auth_type: Optional[str] = None  # Store authentication type information
    package_type: str = "REGISTRY"  # REGISTRY or ARCHIVE
    piece_type: str = "OFFICIAL"   # OFFICIAL or CUSTOM