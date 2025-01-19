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
    input_ui_info: Optional[Dict] = None
    default_value: Optional[Any] = None
    validation_rules: Optional[Dict] = None
    package_type: Optional[str] = None

@dataclass
class StepSettings:
    piece_name: str
    piece_version: str
    action_name: str
    input: Dict[str, Any]
    input_ui_info: Dict[str, Any]
    package_type: str
    error_handling: ErrorHandlingOptions

@dataclass
class BaseComponent:
    name: str
    display_name: str
    description: str
    properties: List[Property]
    piece_name: Optional[str] = None
    piece_version: Optional[str] = None
    settings_template: Optional[StepSettings] = None
    valid: bool = True
    error_handling: Optional[ErrorHandlingOptions] = None
    trigger_type: Optional[str] = None

@dataclass
class Action(BaseComponent):
    pass

@dataclass
class Trigger(BaseComponent):
    trigger_type: str = "PIECE_TRIGGER"

@dataclass
class Piece:
    name: str
    display_name: str
    description: str
    minimum_supported_release: str
    logo_url: str
    actions: List[Action] = field(default_factory=list)
    triggers: List[Trigger] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    auth_type: Optional[str] = None
    package_type: str = "REGISTRY"
    piece_type: str = "OFFICIAL"