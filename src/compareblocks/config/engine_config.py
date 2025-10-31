#!/usr/bin/env python3
"""
NDJSON Engine Configuration Management System

This module provides comprehensive configuration management for OCR engines using NDJSON format.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Iterator
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib
import uuid


class ConfigurationScope(Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    ENGINE = "engine"
    PDF = "pdf"
    SESSION = "session"


class ConfigurationType(Enum):
    """Types of configuration records in NDJSON."""
    PARENT_CONFIG = "parent_config"
    ENGINE_CONFIG = "engine_config"
    PDF_OVERRIDE = "pdf_override"
    HISTORICAL_SETTING = "historical_setting"
    OPTIMIZATION_PROPOSAL = "optimization_proposal"


@dataclass
class CLIParameter:
    """CLI parameter definition for an engine."""
    name: str
    type: str
    description: str
    default: Any = None
    choices: Optional[List[str]] = None
    required: bool = False
    validation: Optional[str] = None
    cli_flag: Optional[str] = None
    tested: bool = False  # Whether this parameter has been tested
    auto_optimize: bool = False  # Whether this parameter is included in auto-optimization
    min_value: Optional[float] = None  # For numeric parameters
    max_value: Optional[float] = None  # For numeric parameters
    category: str = "general"  # Parameter category for GUI grouping


@dataclass
class MCPFunction:
    """MCP function definition with expected attributes."""
    name: str
    description: str
    parameters: Dict[str, Any]
    return_format: Dict[str, Any]
    required_attributes: List[str]
    optional_attributes: List[str]
    version: str = "1.0"


@dataclass
class OptimizationSetting:
    """Optimization setting for specific conditions."""
    condition: str
    parameter_name: str
    value: Any
    confidence: float
    reasoning: str
    performance_impact: str


@dataclass
class EngineConfiguration:
    """Complete engine configuration record."""
    config_id: str
    config_type: ConfigurationType
    engine_name: str
    parent_config_id: Optional[str]
    pdf_hash: Optional[str]
    timestamp: str
    active: bool
    default_settings: Dict[str, Any]
    cli_parameters: List[CLIParameter]
    mcp_functions: List[MCPFunction]
    optimization_settings: List[OptimizationSetting]
    version: str = "1.0"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_ndjson_line(self) -> str:
        """Convert to NDJSON line format."""
        data = asdict(self)
        # Convert enum to string value for JSON serialization
        data['config_type'] = self.config_type.value
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def from_ndjson_line(cls, line: str) -> 'EngineConfiguration':
        """Create from NDJSON line."""
        data = json.loads(line)
        data['config_type'] = ConfigurationType(data['config_type'])
        
        # Handle CLI parameters - support both old and new formats
        cli_params = []
        for param in data['cli_parameters']:
            if isinstance(param, dict):
                # Fill in missing fields for backward compatibility
                param_data = {
                    'name': param.get('name', ''),
                    'type': param.get('type', 'str'),
                    'description': param.get('description', ''),
                    'default': param.get('default'),
                    'choices': param.get('choices'),
                    'required': param.get('required', False),
                    'validation': param.get('validation'),
                    'cli_flag': param.get('cli_flag'),
                    'tested': param.get('tested', False),
                    'auto_optimize': param.get('auto_optimize', False),
                    'min_value': param.get('min_value'),
                    'max_value': param.get('max_value'),
                    'category': param.get('category', 'general')
                }
                cli_params.append(CLIParameter(**param_data))
            else:
                cli_params.append(param)
        data['cli_parameters'] = cli_params
        
        # Handle MCP functions
        mcp_funcs = []
        for func in data['mcp_functions']:
            if isinstance(func, dict):
                func_data = {
                    'name': func.get('name', ''),
                    'description': func.get('description', ''),
                    'parameters': func.get('parameters', {}),
                    'return_format': func.get('return_format', {}),
                    'required_attributes': func.get('required_attributes', []),
                    'optional_attributes': func.get('optional_attributes', []),
                    'version': func.get('version', '1.0')
                }
                mcp_funcs.append(MCPFunction(**func_data))
            else:
                mcp_funcs.append(func)
        data['mcp_functions'] = mcp_funcs
        
        # Handle optimization settings
        opt_settings = []
        for opt in data['optimization_settings']:
            if isinstance(opt, dict):
                opt_data = {
                    'condition': opt.get('condition', ''),
                    'parameter_name': opt.get('parameter_name', ''),
                    'value': opt.get('value'),
                    'confidence': opt.get('confidence', 0.0),
                    'reasoning': opt.get('reasoning', ''),
                    'performance_impact': opt.get('performance_impact', 'unknown')
                }
                opt_settings.append(OptimizationSetting(**opt_data))
            else:
                opt_settings.append(opt)
        data['optimization_settings'] = opt_settings
        
        return cls(**data)


class EngineConfigurationManager:
    """Manages NDJSON-based engine configurations with foreign key relationships."""
    
    def __init__(self, config_file: Path = None):
        """Initialize configuration manager."""
        self.config_file = config_file or Path("config/engine_configurations.ndjson")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_parent_configs()
    
    def _ensure_parent_configs(self):
        """Ensure parent configuration records exist."""
        if not self.config_file.exists():
            self._create_default_parent_configs()
    
    def _create_default_parent_configs(self):
        """Create default parent configuration records."""
        parent_configs = [
            EngineConfiguration(
                config_id=str(uuid.uuid4()),
                config_type=ConfigurationType.PARENT_CONFIG,
                engine_name="global_defaults",
                parent_config_id=None,
                pdf_hash=None,
                timestamp=datetime.now().isoformat(),
                active=True,
                default_settings={
                    "timeout": 30,
                    "max_retries": 3,
                    "output_format": "json",
                    "encoding": "utf-8"
                },
                cli_parameters=[],
                mcp_functions=[],
                optimization_settings=[],
                description="Global default settings for all engines"
            )
        ]
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            for config in parent_configs:
                f.write(config.to_ndjson_line() + '\n')
    
    def add_engine_configuration(self, engine_name: str, parent_config_id: str = None) -> str:
        """Add a new engine configuration with foreign key reference."""
        config_id = str(uuid.uuid4())
        
        default_settings = self._get_engine_defaults(engine_name)
        cli_parameters = self._get_engine_cli_parameters(engine_name)
        mcp_functions = self._get_engine_mcp_functions(engine_name)
        optimization_settings = self._get_engine_optimization_settings(engine_name)
        
        config = EngineConfiguration(
            config_id=config_id,
            config_type=ConfigurationType.ENGINE_CONFIG,
            engine_name=engine_name,
            parent_config_id=parent_config_id or self._get_global_parent_id(),
            pdf_hash=None,
            timestamp=datetime.now().isoformat(),
            active=True,
            default_settings=default_settings,
            cli_parameters=cli_parameters,
            mcp_functions=mcp_functions,
            optimization_settings=optimization_settings,
            description=f"Default configuration for {engine_name} engine"
        )
        
        self._append_configuration(config)
        return config_id
    
    def get_engine_configuration(self, engine_name: str) -> Optional[EngineConfiguration]:
        """Get active engine configuration."""
        configs = list(self._load_configurations())
        return next((c for c in configs if c.config_type == ConfigurationType.ENGINE_CONFIG 
                    and c.engine_name == engine_name and c.active), None)
    
    def add_pdf_override(self, engine_name: str, pdf_path: str, overrides: Dict[str, Any]) -> str:
        """Add PDF-specific configuration override."""
        pdf_hash = self._calculate_pdf_hash(pdf_path)
        config_id = str(uuid.uuid4())
        
        base_config = self.get_engine_configuration(engine_name)
        if not base_config:
            raise ValueError(f"No base configuration found for engine: {engine_name}")
        
        override_config = EngineConfiguration(
            config_id=config_id,
            config_type=ConfigurationType.PDF_OVERRIDE,
            engine_name=engine_name,
            parent_config_id=base_config.config_id,
            pdf_hash=pdf_hash,
            timestamp=datetime.now().isoformat(),
            active=True,
            default_settings=overrides,
            cli_parameters=[],
            mcp_functions=[],
            optimization_settings=[],
            description=f"PDF-specific overrides for {engine_name} on {Path(pdf_path).name}",
            tags=["pdf_override", pdf_hash[:8]]
        )
        
        self._append_configuration(override_config)
        return config_id
    
    def get_effective_configuration(self, engine_name: str, pdf_path: str = None) -> Dict[str, Any]:
        """Get effective configuration by merging parent, engine, and PDF-specific settings."""
        configs = list(self._load_configurations())
        
        global_config = next((c for c in configs if c.config_type == ConfigurationType.PARENT_CONFIG 
                             and c.engine_name == "global_defaults"), None)
        effective_settings = global_config.default_settings.copy() if global_config else {}
        
        engine_config = next((c for c in configs if c.config_type == ConfigurationType.ENGINE_CONFIG 
                             and c.engine_name == engine_name and c.active), None)
        if engine_config:
            effective_settings.update(engine_config.default_settings)
        
        if pdf_path:
            pdf_hash = self._calculate_pdf_hash(pdf_path)
            pdf_override = next((c for c in configs if c.config_type == ConfigurationType.PDF_OVERRIDE 
                               and c.engine_name == engine_name and c.pdf_hash == pdf_hash and c.active), None)
            if pdf_override:
                effective_settings.update(pdf_override.default_settings)
        
        return effective_settings
    
    def get_parameter_status(self, engine_name: str) -> Dict[str, Dict[str, Any]]:
        """Get parameter status information for GUI awareness."""
        config = self.get_engine_configuration(engine_name)
        if not config:
            return {}
        
        status = {}
        effective_settings = self.get_effective_configuration(engine_name)
        
        for param in config.cli_parameters:
            current_value = effective_settings.get(param.name, param.default)
            is_default = current_value == param.default
            is_overridden = param.name in effective_settings and not is_default
            
            status[param.name] = {
                "current_value": current_value,
                "default_value": param.default,
                "is_default": is_default,
                "is_overridden": is_overridden,
                "tested": param.tested,
                "auto_optimize": param.auto_optimize,
                "category": param.category,
                "description": param.description,
                "type": param.type,
                "choices": param.choices,
                "min_value": param.min_value,
                "max_value": param.max_value,
                "cli_flag": param.cli_flag
            }
        
        return status
    
    def get_tested_parameters(self, engine_name: str) -> List[str]:
        """Get list of tested parameters for an engine."""
        config = self.get_engine_configuration(engine_name)
        if not config:
            return []
        
        return [param.name for param in config.cli_parameters if param.tested]
    
    def get_auto_optimize_parameters(self, engine_name: str) -> List[str]:
        """Get list of parameters included in auto-optimization."""
        config = self.get_engine_configuration(engine_name)
        if not config:
            return []
        
        return [param.name for param in config.cli_parameters if param.auto_optimize]
    
    def get_parameters_by_category(self, engine_name: str) -> Dict[str, List[str]]:
        """Get parameters grouped by category for GUI organization."""
        config = self.get_engine_configuration(engine_name)
        if not config:
            return {}
        
        categories = {}
        for param in config.cli_parameters:
            category = param.category
            if category not in categories:
                categories[category] = []
            categories[category].append(param.name)
        
        return categories
    
    def validate_parameter_value(self, engine_name: str, param_name: str, value: Any) -> tuple[bool, str]:
        """Validate a parameter value against its constraints."""
        config = self.get_engine_configuration(engine_name)
        if not config:
            return False, f"No configuration found for engine: {engine_name}"
        
        param = next((p for p in config.cli_parameters if p.name == param_name), None)
        if not param:
            return False, f"Parameter {param_name} not found for engine {engine_name}"
        
        # Type validation
        if param.type == "int":
            try:
                int_value = int(value)
                if param.min_value is not None and int_value < param.min_value:
                    return False, f"Value {int_value} is below minimum {param.min_value}"
                if param.max_value is not None and int_value > param.max_value:
                    return False, f"Value {int_value} is above maximum {param.max_value}"
            except ValueError:
                return False, f"Value {value} is not a valid integer"
        
        elif param.type == "float":
            try:
                float_value = float(value)
                if param.min_value is not None and float_value < param.min_value:
                    return False, f"Value {float_value} is below minimum {param.min_value}"
                if param.max_value is not None and float_value > param.max_value:
                    return False, f"Value {float_value} is above maximum {param.max_value}"
            except ValueError:
                return False, f"Value {value} is not a valid float"
        
        elif param.type == "bool":
            if not isinstance(value, bool) and str(value).lower() not in ['true', 'false', '0', '1']:
                return False, f"Value {value} is not a valid boolean"
        
        elif param.type == "choice":
            if param.choices and str(value) not in param.choices:
                return False, f"Value {value} is not in allowed choices: {param.choices}"
        
        # Custom validation if specified
        if param.validation:
            try:
                # Simple validation expressions like "len(value) > 0"
                if not eval(param.validation, {"value": value, "len": len}):
                    return False, f"Value {value} failed validation: {param.validation}"
            except Exception as e:
                return False, f"Validation error: {str(e)}"
        
        return True, "Valid"
    
    def get_parameter_usage_stats(self, engine_name: str) -> Dict[str, Dict[str, Any]]:
        """Get usage statistics for parameters across all PDF overrides."""
        configs = list(self._load_configurations())
        
        # Get all PDF overrides for this engine
        pdf_overrides = [c for c in configs if c.config_type == ConfigurationType.PDF_OVERRIDE 
                        and c.engine_name == engine_name and c.active]
        
        stats = {}
        config = self.get_engine_configuration(engine_name)
        if not config:
            return stats
        
        for param in config.cli_parameters:
            param_name = param.name
            override_count = sum(1 for override in pdf_overrides if param_name in override.default_settings)
            
            # Collect all values used for this parameter
            values_used = []
            for override in pdf_overrides:
                if param_name in override.default_settings:
                    values_used.append(override.default_settings[param_name])
            
            stats[param_name] = {
                "override_count": override_count,
                "total_pdfs": len(pdf_overrides),
                "usage_percentage": (override_count / len(pdf_overrides) * 100) if pdf_overrides else 0,
                "values_used": list(set(values_used)),  # Unique values
                "most_common_override": max(set(values_used), key=values_used.count) if values_used else None
            }
        
        return stats
    
    def _get_engine_defaults(self, engine_name: str) -> Dict[str, Any]:
        """Get default settings for specific engine type."""
        defaults = {
            "tesseract": {
                # Core OCR settings
                "dpi": 300,
                "psm": 6,
                "oem": 3,
                "lang": "eng",
                # Advanced settings
                "preserve_interword_spaces": 1,
                "user_words_suffix": None,
                "user_patterns_suffix": None,
                # Performance settings
                "tessedit_char_whitelist": None,
                "tessedit_char_blacklist": None,
                "tessedit_pageseg_mode": 6,
                # Output settings
                "tessedit_create_hocr": 0,
                "tessedit_create_pdf": 0,
                "tessedit_create_txt": 1
            },
            "paddleocr": {
                # Core settings
                "use_angle_cls": True,
                "lang": "en",
                "use_gpu": False,
                "show_log": False,
                # Detection settings
                "det_algorithm": "DB",
                "det_model_dir": None,
                "det_limit_side_len": 960,
                "det_limit_type": "max",
                # Recognition settings
                "rec_algorithm": "SVTR_LCNet",
                "rec_model_dir": None,
                "rec_image_shape": "3, 48, 320",
                "rec_batch_num": 6,
                # Classification settings
                "cls_model_dir": None,
                "cls_image_shape": "3, 48, 192",
                "cls_batch_num": 6,
                "cls_thresh": 0.9
            },
            "pymupdf": {
                # Extraction settings
                "extract_images": False,
                "extract_fonts": True,
                "extract_text": True,
                "sort_blocks": True,
                # Text extraction settings
                "flags": 0,  # TEXT_PRESERVE_LIGATURES | TEXT_PRESERVE_WHITESPACE
                "clip": None,
                "textpage": None,
                # Block processing
                "dehyphenate": True,
                "keep_chars": None,
                "tolerance": 3.0
            },
            "docling": {
                # Core settings
                "format": "json",
                "extract_tables": True,
                "extract_images": False,
                "extract_figures": True,
                # Processing settings
                "ocr_enabled": True,
                "table_structure_enabled": True,
                "figure_classification_enabled": True,
                # Output settings
                "include_metadata": True,
                "include_page_breaks": True
            },
            "kreuzberg": {
                # Model settings
                "model": "default",
                "confidence_threshold": 0.8,
                "batch_size": 1,
                # Processing settings
                "use_gpu": False,
                "max_image_size": 2048,
                "preprocessing": True
            }
        }
        return defaults.get(engine_name, {})
    
    def _get_engine_cli_parameters(self, engine_name: str) -> List[CLIParameter]:
        """Get CLI parameters for specific engine type."""
        cli_params = {
            "tesseract": [
                # Core OCR parameters
                CLIParameter(
                    name="dpi", type="int", description="Image DPI for OCR processing",
                    default=300, cli_flag="--dpi", tested=True, auto_optimize=True,
                    min_value=72, max_value=600, category="image_processing"
                ),
                CLIParameter(
                    name="psm", type="choice", description="Page segmentation mode",
                    default=6, choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"],
                    cli_flag="--psm", tested=True, auto_optimize=True, category="segmentation"
                ),
                CLIParameter(
                    name="oem", type="choice", description="OCR Engine Mode",
                    default=3, choices=["0", "1", "2", "3"], cli_flag="--oem",
                    tested=True, auto_optimize=False, category="engine"
                ),
                CLIParameter(
                    name="lang", type="str", description="Language for OCR",
                    default="eng", cli_flag="-l", tested=True, auto_optimize=False,
                    category="language"
                ),
                # Advanced parameters
                CLIParameter(
                    name="preserve_interword_spaces", type="choice", description="Preserve spaces between words",
                    default=1, choices=["0", "1"], cli_flag="-c preserve_interword_spaces",
                    tested=True, auto_optimize=False, category="text_processing"
                ),
                CLIParameter(
                    name="tessedit_char_whitelist", type="str", description="Whitelist of allowed characters",
                    default=None, cli_flag="-c tessedit_char_whitelist", tested=True,
                    auto_optimize=False, category="character_filtering"
                ),
                CLIParameter(
                    name="tessedit_char_blacklist", type="str", description="Blacklist of forbidden characters",
                    default=None, cli_flag="-c tessedit_char_blacklist", tested=True,
                    auto_optimize=False, category="character_filtering"
                ),
                CLIParameter(
                    name="tessedit_create_hocr", type="choice", description="Create hOCR output",
                    default=0, choices=["0", "1"], cli_flag="-c tessedit_create_hocr",
                    tested=True, auto_optimize=False, category="output"
                ),
                CLIParameter(
                    name="tessedit_create_pdf", type="choice", description="Create searchable PDF",
                    default=0, choices=["0", "1"], cli_flag="-c tessedit_create_pdf",
                    tested=True, auto_optimize=False, category="output"
                )
            ],
            "paddleocr": [
                # Core parameters
                CLIParameter(
                    name="use_gpu", type="bool", description="Use GPU acceleration",
                    default=False, tested=True, auto_optimize=True, category="performance"
                ),
                CLIParameter(
                    name="lang", type="choice", description="Language for OCR",
                    default="en", choices=["en", "ch", "fr", "german", "korean", "japan", "it", "es", "pt", "ru", "ar", "ta", "ug", "fa", "ur", "rs", "oc", "rsc", "bg", "uk", "be", "te", "kn", "ch_tra", "hi", "mr", "ne", "latin", "devanagari"],
                    tested=True, auto_optimize=False, category="language"
                ),
                CLIParameter(
                    name="use_angle_cls", type="bool", description="Use angle classification",
                    default=True, tested=True, auto_optimize=True, category="preprocessing"
                ),
                CLIParameter(
                    name="show_log", type="bool", description="Show detailed logs",
                    default=False, tested=True, auto_optimize=False, category="debugging"
                ),
                # Detection parameters
                CLIParameter(
                    name="det_algorithm", type="choice", description="Text detection algorithm",
                    default="DB", choices=["DB", "EAST", "SAST"], tested=True,
                    auto_optimize=False, category="detection"
                ),
                CLIParameter(
                    name="det_limit_side_len", type="int", description="Detection limit side length",
                    default=960, tested=True, auto_optimize=True, min_value=320, max_value=2048,
                    category="detection"
                ),
                CLIParameter(
                    name="det_limit_type", type="choice", description="Detection limit type",
                    default="max", choices=["max", "min"], tested=True, auto_optimize=False,
                    category="detection"
                ),
                # Recognition parameters
                CLIParameter(
                    name="rec_algorithm", type="choice", description="Text recognition algorithm",
                    default="SVTR_LCNet", choices=["SVTR_LCNet", "CRNN", "RARE", "SRN"],
                    tested=True, auto_optimize=False, category="recognition"
                ),
                CLIParameter(
                    name="rec_batch_num", type="int", description="Recognition batch size",
                    default=6, tested=True, auto_optimize=True, min_value=1, max_value=32,
                    category="performance"
                ),
                # Classification parameters
                CLIParameter(
                    name="cls_batch_num", type="int", description="Classification batch size",
                    default=6, tested=True, auto_optimize=True, min_value=1, max_value=32,
                    category="performance"
                ),
                CLIParameter(
                    name="cls_thresh", type="float", description="Classification threshold",
                    default=0.9, tested=True, auto_optimize=True, min_value=0.1, max_value=1.0,
                    category="classification"
                )
            ],
            "pymupdf": [
                # PyMuPDF uses library calls, not CLI, but we define parameters for consistency
                CLIParameter(
                    name="extract_images", type="bool", description="Extract images from PDF",
                    default=False, tested=True, auto_optimize=True, category="extraction"
                ),
                CLIParameter(
                    name="extract_fonts", type="bool", description="Extract font information",
                    default=True, tested=True, auto_optimize=False, category="extraction"
                ),
                CLIParameter(
                    name="extract_text", type="bool", description="Extract text content",
                    default=True, tested=True, auto_optimize=False, category="extraction"
                ),
                CLIParameter(
                    name="sort_blocks", type="bool", description="Sort text blocks by position",
                    default=True, tested=True, auto_optimize=False, category="text_processing"
                ),
                CLIParameter(
                    name="flags", type="int", description="Text extraction flags",
                    default=0, tested=True, auto_optimize=False, min_value=0, max_value=15,
                    category="text_processing"
                ),
                CLIParameter(
                    name="dehyphenate", type="bool", description="Remove hyphenation",
                    default=True, tested=True, auto_optimize=True, category="text_processing"
                ),
                CLIParameter(
                    name="tolerance", type="float", description="Text block tolerance",
                    default=3.0, tested=True, auto_optimize=True, min_value=0.1, max_value=10.0,
                    category="text_processing"
                )
            ],
            "docling": [
                CLIParameter(
                    name="format", type="choice", description="Output format",
                    default="json", choices=["json", "markdown", "text"], tested=True,
                    auto_optimize=False, category="output"
                ),
                CLIParameter(
                    name="extract_tables", type="bool", description="Extract table structures",
                    default=True, tested=True, auto_optimize=True, category="extraction"
                ),
                CLIParameter(
                    name="extract_images", type="bool", description="Extract images",
                    default=False, tested=True, auto_optimize=True, category="extraction"
                ),
                CLIParameter(
                    name="extract_figures", type="bool", description="Extract figures",
                    default=True, tested=True, auto_optimize=True, category="extraction"
                ),
                CLIParameter(
                    name="ocr_enabled", type="bool", description="Enable OCR for images",
                    default=True, tested=True, auto_optimize=True, category="ocr"
                ),
                CLIParameter(
                    name="table_structure_enabled", type="bool", description="Enable table structure detection",
                    default=True, tested=True, auto_optimize=False, category="tables"
                ),
                CLIParameter(
                    name="figure_classification_enabled", type="bool", description="Enable figure classification",
                    default=True, tested=True, auto_optimize=False, category="figures"
                ),
                CLIParameter(
                    name="include_metadata", type="bool", description="Include document metadata",
                    default=True, tested=True, auto_optimize=False, category="output"
                ),
                CLIParameter(
                    name="include_page_breaks", type="bool", description="Include page break markers",
                    default=True, tested=True, auto_optimize=False, category="output"
                )
            ],
            "kreuzberg": [
                CLIParameter(
                    name="model", type="choice", description="Model to use for processing",
                    default="default", choices=["default", "fast", "accurate"], tested=True,
                    auto_optimize=True, category="model"
                ),
                CLIParameter(
                    name="confidence_threshold", type="float", description="Confidence threshold for results",
                    default=0.8, tested=True, auto_optimize=True, min_value=0.1, max_value=1.0,
                    category="quality"
                ),
                CLIParameter(
                    name="batch_size", type="int", description="Processing batch size",
                    default=1, tested=True, auto_optimize=True, min_value=1, max_value=16,
                    category="performance"
                ),
                CLIParameter(
                    name="use_gpu", type="bool", description="Use GPU acceleration",
                    default=False, tested=True, auto_optimize=True, category="performance"
                ),
                CLIParameter(
                    name="max_image_size", type="int", description="Maximum image size for processing",
                    default=2048, tested=True, auto_optimize=True, min_value=512, max_value=4096,
                    category="image_processing"
                ),
                CLIParameter(
                    name="preprocessing", type="bool", description="Enable image preprocessing",
                    default=True, tested=True, auto_optimize=True, category="preprocessing"
                )
            ]
        }
        return cli_params.get(engine_name, [])
    
    def _get_engine_mcp_functions(self, engine_name: str) -> List[MCPFunction]:
        """Get MCP functions for specific engine type."""
        mcp_functions = {
            "tesseract": [
                MCPFunction(
                    name="tesseract_extract",
                    description="Extract text using Tesseract OCR",
                    parameters={
                        "image_path": "str",
                        "config": "dict",
                        "dpi": "int",
                        "psm": "int",
                        "oem": "int",
                        "lang": "str"
                    },
                    return_format={
                        "text": "str",
                        "confidence": "float",
                        "boxes": "list",
                        "words": "list",
                        "lines": "list"
                    },
                    required_attributes=["text"],
                    optional_attributes=["confidence", "boxes", "words", "lines", "metadata"]
                ),
                MCPFunction(
                    name="tesseract_batch_extract",
                    description="Batch extract text from multiple images",
                    parameters={
                        "image_paths": "list",
                        "config": "dict",
                        "parallel": "bool"
                    },
                    return_format={
                        "results": "list",
                        "total_processed": "int",
                        "errors": "list"
                    },
                    required_attributes=["results"],
                    optional_attributes=["total_processed", "errors", "processing_time"]
                )
            ],
            "paddleocr": [
                MCPFunction(
                    name="paddleocr_extract",
                    description="Extract text using PaddleOCR",
                    parameters={
                        "image_path": "str",
                        "lang": "str",
                        "use_angle_cls": "bool",
                        "use_gpu": "bool"
                    },
                    return_format={
                        "text": "str",
                        "boxes": "list",
                        "scores": "list",
                        "angles": "list"
                    },
                    required_attributes=["text", "boxes"],
                    optional_attributes=["scores", "angles", "processing_time"]
                ),
                MCPFunction(
                    name="paddleocr_detect_only",
                    description="Detect text regions without recognition",
                    parameters={
                        "image_path": "str",
                        "det_algorithm": "str"
                    },
                    return_format={
                        "boxes": "list",
                        "scores": "list"
                    },
                    required_attributes=["boxes"],
                    optional_attributes=["scores"]
                )
            ],
            "pymupdf": [
                MCPFunction(
                    name="pymupdf_extract_text",
                    description="Extract text from PDF using PyMuPDF",
                    parameters={
                        "pdf_path": "str",
                        "page_range": "tuple",
                        "flags": "int",
                        "sort_blocks": "bool"
                    },
                    return_format={
                        "text": "str",
                        "blocks": "list",
                        "fonts": "list",
                        "images": "list"
                    },
                    required_attributes=["text", "blocks"],
                    optional_attributes=["fonts", "images", "metadata"]
                ),
                MCPFunction(
                    name="pymupdf_get_page_info",
                    description="Get page information and structure",
                    parameters={
                        "pdf_path": "str",
                        "page_num": "int"
                    },
                    return_format={
                        "width": "float",
                        "height": "float",
                        "rotation": "int",
                        "blocks": "list"
                    },
                    required_attributes=["width", "height", "blocks"],
                    optional_attributes=["rotation", "mediabox", "cropbox"]
                )
            ],
            "docling": [
                MCPFunction(
                    name="docling_convert",
                    description="Convert document using Docling",
                    parameters={
                        "input_path": "str",
                        "output_format": "str",
                        "extract_tables": "bool",
                        "extract_images": "bool"
                    },
                    return_format={
                        "content": "str",
                        "tables": "list",
                        "images": "list",
                        "metadata": "dict"
                    },
                    required_attributes=["content"],
                    optional_attributes=["tables", "images", "metadata"]
                )
            ],
            "kreuzberg": [
                MCPFunction(
                    name="kreuzberg_process",
                    description="Process document using Kreuzberg",
                    parameters={
                        "input_path": "str",
                        "model": "str",
                        "confidence_threshold": "float"
                    },
                    return_format={
                        "text": "str",
                        "confidence": "float",
                        "entities": "list"
                    },
                    required_attributes=["text"],
                    optional_attributes=["confidence", "entities", "processing_info"]
                )
            ]
        }
        return mcp_functions.get(engine_name, [])
    
    def _get_engine_optimization_settings(self, engine_name: str) -> List[OptimizationSetting]:
        """Get default optimization settings for engine type."""
        return []
    
    def _load_configurations(self) -> Iterator[EngineConfiguration]:
        """Load all configurations from NDJSON file."""
        if not self.config_file.exists():
            return
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    yield EngineConfiguration.from_ndjson_line(line)
    
    def _append_configuration(self, config: EngineConfiguration):
        """Append configuration to NDJSON file."""
        with open(self.config_file, 'a', encoding='utf-8') as f:
            f.write(config.to_ndjson_line() + '\n')
    
    def _get_global_parent_id(self) -> str:
        """Get the global parent configuration ID."""
        configs = list(self._load_configurations())
        global_config = next((c for c in configs if c.config_type == ConfigurationType.PARENT_CONFIG 
                             and c.engine_name == "global_defaults"), None)
        return global_config.config_id if global_config else None
    
    def _calculate_pdf_hash(self, pdf_path: str) -> str:
        """Calculate hash for PDF file."""
        if pdf_path.startswith("pdf_hash_"):
            return pdf_path.replace("pdf_hash_", "")
        
        try:
            with open(pdf_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except FileNotFoundError:
            return hashlib.md5(pdf_path.encode()).hexdigest()
    
    def create_individual_config_files(self) -> Dict[str, str]:
        """Create individual configuration files for each engine with foreign key references."""
        config_dir = Path("config/engines")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = {}
        configs = list(self._load_configurations())
        
        # Group configurations by engine
        engine_configs = {}
        for config in configs:
            if config.config_type == ConfigurationType.ENGINE_CONFIG:
                engine_configs[config.engine_name] = config
        
        # Create individual files
        for engine_name, config in engine_configs.items():
            config_file = config_dir / f"{engine_name}_config.json"
            
            # Create comprehensive config structure
            individual_config = {
                "engine_name": engine_name,
                "config_id": config.config_id,
                "parent_config_reference": {
                    "parent_config_id": config.parent_config_id,
                    "parent_file": "config/engine_configurations.ndjson",
                    "foreign_key_type": "parent_config_id"
                },
                "default_optimization_settings": {
                    param.name: {
                        "default_value": param.default,
                        "auto_optimize": param.auto_optimize,
                        "tested": param.tested,
                        "category": param.category,
                        "type": param.type,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "choices": param.choices
                    }
                    for param in config.cli_parameters
                },
                "supported_cli_parameters": [
                    {
                        "name": param.name,
                        "type": param.type,
                        "description": param.description,
                        "default": param.default,
                        "choices": param.choices,
                        "required": param.required,
                        "validation": param.validation,
                        "cli_flag": param.cli_flag,
                        "tested": param.tested,
                        "auto_optimize": param.auto_optimize,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "category": param.category
                    }
                    for param in config.cli_parameters
                ],
                "supported_mcp_functions": [
                    {
                        "name": func.name,
                        "description": func.description,
                        "parameters": func.parameters,
                        "return_format": func.return_format,
                        "required_attributes": func.required_attributes,
                        "optional_attributes": func.optional_attributes,
                        "version": func.version
                    }
                    for func in config.mcp_functions
                ],
                "cli_support": len(config.cli_parameters) > 0,
                "mcp_support": len(config.mcp_functions) > 0,
                "version": config.version,
                "last_updated": datetime.now().isoformat(),
                "description": config.description
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(individual_config, f, indent=2, ensure_ascii=False)
            
            created_files[engine_name] = str(config_file)
        
        return created_files
    
    def approve_optimization_proposal(self, proposal_id: str) -> str:
        """Approve an optimization proposal and create PDF override."""
        configs = list(self._load_configurations())
        
        # Find the proposal
        proposal = next((c for c in configs if c.config_id == proposal_id 
                        and c.config_type == ConfigurationType.OPTIMIZATION_PROPOSAL), None)
        
        if not proposal:
            raise ValueError(f"Optimization proposal not found: {proposal_id}")
        
        # Create PDF override from proposal
        override_settings = {}
        for opt_setting in proposal.optimization_settings:
            override_settings[opt_setting.parameter_name] = opt_setting.value
        
        # Create the override
        override_id = self.add_pdf_override(
            proposal.engine_name,
            f"pdf_hash_{proposal.pdf_hash}",  # Reconstruct path from hash
            override_settings
        )
        
        # Mark proposal as approved (active=True)
        self._update_configuration_status(proposal_id, active=True)
        
        return override_id
    
    def _update_configuration_status(self, config_id: str, active: bool):
        """Update the active status of a configuration."""
        configs = list(self._load_configurations())
        
        # Find and update the configuration
        updated_configs = []
        for config in configs:
            if config.config_id == config_id:
                config.active = active
                config.timestamp = datetime.now().isoformat()
            updated_configs.append(config)
        
        # Rewrite the entire file
        with open(self.config_file, 'w', encoding='utf-8') as f:
            for config in updated_configs:
                f.write(config.to_ndjson_line() + '\n')
    
    def create_optimization_proposal(self, engine_name: str, pdf_path: str, 
                                   proposed_settings: List[OptimizationSetting]) -> str:
        """Create an optimization proposal for review."""
        pdf_hash = self._calculate_pdf_hash(pdf_path)
        config_id = str(uuid.uuid4())
        
        proposal = EngineConfiguration(
            config_id=config_id,
            config_type=ConfigurationType.OPTIMIZATION_PROPOSAL,
            engine_name=engine_name,
            parent_config_id=None,
            pdf_hash=pdf_hash,
            timestamp=datetime.now().isoformat(),
            active=False,  # Pending approval
            default_settings={},
            cli_parameters=[],
            mcp_functions=[],
            optimization_settings=proposed_settings,
            description=f"Optimization proposal for {engine_name} on {Path(pdf_path).name}",
            tags=["proposal", "optimization", pdf_hash[:8]]
        )
        
        self._append_configuration(proposal)
        return config_id
    
    def get_pdf_configuration_history(self, engine_name: str, pdf_path: str) -> List[EngineConfiguration]:
        """Get historical configurations for a specific PDF."""
        pdf_hash = self._calculate_pdf_hash(pdf_path)
        configs = list(self._load_configurations())
        
        # Get all configurations for this engine and PDF, sorted by timestamp
        pdf_configs = [
            c for c in configs 
            if c.engine_name == engine_name and c.pdf_hash == pdf_hash
            and c.config_type in [ConfigurationType.PDF_OVERRIDE, ConfigurationType.HISTORICAL_SETTING]
        ]
        
        # Sort by timestamp (newest first)
        pdf_configs.sort(key=lambda x: x.timestamp, reverse=True)
        return pdf_configs
    
    def archive_current_pdf_override(self, engine_name: str, pdf_path: str) -> str:
        """Archive current PDF override as historical setting before creating new one."""
        pdf_hash = self._calculate_pdf_hash(pdf_path)
        configs = list(self._load_configurations())
        
        # Find current active override
        current_override = next((c for c in configs if c.config_type == ConfigurationType.PDF_OVERRIDE 
                               and c.engine_name == engine_name and c.pdf_hash == pdf_hash and c.active), None)
        
        if not current_override:
            return None  # No current override to archive
        
        # Create historical record
        historical_id = str(uuid.uuid4())
        historical_config = EngineConfiguration(
            config_id=historical_id,
            config_type=ConfigurationType.HISTORICAL_SETTING,
            engine_name=engine_name,
            parent_config_id=current_override.parent_config_id,
            pdf_hash=pdf_hash,
            timestamp=current_override.timestamp,  # Keep original timestamp
            active=False,
            default_settings=current_override.default_settings.copy(),
            cli_parameters=[],
            mcp_functions=[],
            optimization_settings=[],
            description=f"Historical settings for {engine_name} on {Path(pdf_path).name} (archived at {datetime.now().isoformat()})",
            tags=["historical", "archived", pdf_hash[:8]]
        )
        
        # Deactivate current override
        self._update_configuration_status(current_override.config_id, active=False)
        
        # Add historical record
        self._append_configuration(historical_config)
        
        return historical_id
    
    def get_pending_optimization_proposals(self) -> List[EngineConfiguration]:
        """Get all pending optimization proposals."""
        configs = list(self._load_configurations())
        return [c for c in configs if c.config_type == ConfigurationType.OPTIMIZATION_PROPOSAL and not c.active]
    
    def get_engine_statistics(self, engine_name: str) -> Dict[str, Any]:
        """Get comprehensive statistics for an engine."""
        configs = list(self._load_configurations())
        
        # Filter configurations for this engine
        engine_configs = [c for c in configs if c.engine_name == engine_name]
        
        # Count by type
        type_counts = {}
        for config_type in ConfigurationType:
            type_counts[config_type.value] = len([c for c in engine_configs if c.config_type == config_type])
        
        # PDF-specific statistics
        pdf_overrides = [c for c in engine_configs if c.config_type == ConfigurationType.PDF_OVERRIDE and c.active]
        unique_pdfs = len(set(c.pdf_hash for c in pdf_overrides if c.pdf_hash))
        
        # Parameter usage statistics
        param_stats = self.get_parameter_usage_stats(engine_name)
        
        return {
            "engine_name": engine_name,
            "total_configurations": len(engine_configs),
            "configuration_types": type_counts,
            "active_pdf_overrides": len(pdf_overrides),
            "unique_pdfs_configured": unique_pdfs,
            "parameter_usage": param_stats,
            "last_updated": max((c.timestamp for c in engine_configs), default="Never")
        }