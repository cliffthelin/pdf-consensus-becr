#!/usr/bin/env python3
"""
Enhanced script to add comprehensive field attributes, side effects, dependencies, 
and other supporting fields to functions in the catalog that are missing values.
"""

import json
import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

class CatalogFieldEnhancer:
    """Enhanced field attributes processor for function catalog."""
    
    def __init__(self):
        self.enhanced_count = 0
        self.skipped_count = 0
        
    def analyze_function_signature(self, func_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze function signature to extract parameter information."""
        parameters = func_entry.get("parameters", [])
        param_info = {}
        
        for param in parameters:
            # Skip if already a dict (pre-processed) or self parameter
            if isinstance(param, dict) or param == "self":
                continue
                
            # Parse parameter with type hints and defaults
            param_name = param.split(":")[0].split("=")[0].strip()
            
            # Extract type hint if present
            if ":" in param:
                type_part = param.split(":")[1].split("=")[0].strip()
                param_info[param_name] = {
                    "type": type_part,
                    "constraint": self._infer_constraint_from_type(type_part),
                    "description": f"Parameter {param_name}"
                }
            else:
                param_info[param_name] = {
                    "type": "Any",
                    "constraint": "valid input",
                    "description": f"Parameter {param_name}"
                }
                
            # Check for default values
            if "=" in param:
                default_val = param.split("=")[1].strip()
                param_info[param_name]["default"] = default_val
                
        return param_info
    
    def _infer_constraint_from_type(self, type_hint: str) -> str:
        """Infer constraints based on type hints."""
        type_hint = type_hint.lower()
        
        if "int" in type_hint:
            return ">= 0"
        elif "float" in type_hint:
            return ">= 0.0"
        elif "str" in type_hint:
            return "non-empty string"
        elif "bool" in type_hint:
            return "boolean value"
        elif "list" in type_hint:
            return "valid list"
        elif "dict" in type_hint:
            return "valid dictionary"
        elif "path" in type_hint:
            return "valid file path"
        else:
            return "valid input"
    
    def infer_dependencies(self, func_entry: Dict[str, Any]) -> List[str]:
        """Infer dependencies based on function characteristics."""
        func_name = func_entry["function_name"]
        module = func_entry["module"]
        dependencies = []
        
        # Module-based dependencies
        if "io" in module:
            dependencies.extend(["pathlib", "json"])
        elif "gbg" in module:
            dependencies.extend(["fitz", "PyMuPDF"])
        elif "gui" in module:
            dependencies.extend(["PySide6"])
        elif "analytics" in module:
            dependencies.extend(["pandas", "numpy"])
        elif "engines" in module:
            dependencies.extend(["fitz", "PyMuPDF"])
        elif "consensus" in module:
            dependencies.extend(["statistics"])
        elif "features" in module:
            dependencies.extend(["langdetect", "rapidfuzz"])
        elif "normalize" in module:
            dependencies.extend(["re", "unicodedata"])
        elif "association" in module:
            dependencies.extend(["numpy"])
        elif "config" in module:
            dependencies.extend(["pathlib", "json"])
        elif "debug" in module:
            dependencies.extend(["PIL", "matplotlib"])
        elif "testing" in module:
            dependencies.extend(["pytest", "time"])
            
        # Function name-based dependencies
        if "pdf" in func_name.lower():
            dependencies.extend(["fitz", "PyMuPDF"])
        if "image" in func_name.lower():
            dependencies.extend(["PIL", "cv2"])
        if "validate" in func_name.lower():
            dependencies.extend(["jsonschema"])
        if "load" in func_name.lower() or "save" in func_name.lower():
            dependencies.extend(["pathlib"])
        if "match" in func_name.lower():
            dependencies.extend(["rapidfuzz"])
        if "ocr" in func_name.lower():
            dependencies.extend(["tesseract", "paddleocr"])
        if "gui" in func_name.lower() or "dialog" in func_name.lower():
            dependencies.extend(["PySide6"])
            
        return list(set(dependencies))  # Remove duplicates
    
    def infer_side_effects(self, func_entry: Dict[str, Any]) -> List[str]:
        """Infer side effects based on function characteristics."""
        func_name = func_entry["function_name"]
        module = func_entry["module"]
        side_effects = []
        
        # Common side effects based on function patterns
        if func_name.endswith(".__init__"):
            side_effects.append("Initializes object state")
        elif func_name.endswith(".__post_init__"):
            side_effects.append("Validates object state")
            side_effects.append("May raise ValueError on validation failure")
        elif "validate" in func_name.lower():
            side_effects.append("May raise ValidationError")
        elif "load" in func_name.lower() or "read" in func_name.lower():
            side_effects.append("File I/O operations")
            side_effects.append("May raise FileNotFoundError")
        elif "save" in func_name.lower() or "write" in func_name.lower():
            side_effects.append("File I/O operations")
            side_effects.append("Creates or modifies files")
        elif "pdf" in func_name.lower():
            side_effects.append("Opens/closes PDF documents")
            side_effects.append("Memory allocation for PDF processing")
        elif "gui" in module or "dialog" in func_name.lower():
            side_effects.append("GUI state changes")
            side_effects.append("User interaction events")
        elif "config" in func_name.lower():
            side_effects.append("Configuration state changes")
        elif "cache" in func_name.lower():
            side_effects.append("Cache state modifications")
        elif "log" in func_name.lower():
            side_effects.append("Logging operations")
        elif "process" in func_name.lower():
            side_effects.append("Processing state changes")
            
        return side_effects
    
    def enhance_return_value_attributes(self, func_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance return value attributes based on return type and function purpose."""
        return_type = func_entry.get("return_type", "None")
        func_name = func_entry["function_name"]
        
        if return_type == "None":
            return {}
            
        return_attrs = {
            "type": return_type,
            "constraint": self._infer_return_constraint(return_type, func_name),
            "description": self._infer_return_description(return_type, func_name)
        }
        
        # Add specific constraints based on function purpose
        if "iou" in func_name.lower() or "score" in func_name.lower():
            if return_type == "float":
                return_attrs["constraint"] = "0.0 <= value <= 1.0"
                return_attrs["description"] = "Normalized score or IoU value"
        elif "count" in func_name.lower() or "length" in func_name.lower():
            if return_type == "int":
                return_attrs["constraint"] = ">= 0"
                return_attrs["description"] = "Count or length value"
        elif "path" in func_name.lower():
            if return_type == "str":
                return_attrs["constraint"] = "valid file path"
                return_attrs["description"] = "File or directory path"
        elif "validate" in func_name.lower():
            if return_type == "bool":
                return_attrs["description"] = "Validation result"
        elif "extract" in func_name.lower() or "get" in func_name.lower():
            if return_type.startswith("List"):
                return_attrs["description"] = "Extracted or retrieved items"
        elif "create" in func_name.lower() or "build" in func_name.lower():
            return_attrs["description"] = "Created or built object"
            
        return return_attrs
    
    def _infer_return_constraint(self, return_type: str, func_name: str) -> str:
        """Infer return value constraints."""
        if return_type == "str":
            return "non-empty string" if "get" in func_name.lower() else "valid string"
        elif return_type == "int":
            return ">= 0" if any(word in func_name.lower() for word in ["count", "size", "length"]) else "valid integer"
        elif return_type == "float":
            return "0.0 <= value <= 1.0" if any(word in func_name.lower() for word in ["score", "iou", "ratio"]) else ">= 0.0"
        elif return_type == "bool":
            return "boolean value"
        elif return_type.startswith("List"):
            return "non-empty list" if "extract" in func_name.lower() else "valid list"
        elif return_type.startswith("Dict"):
            return "valid dictionary"
        elif return_type.startswith("tuple"):
            return "valid tuple"
        else:
            return "valid return value"
    
    def _infer_return_description(self, return_type: str, func_name: str) -> str:
        """Infer return value description."""
        if "extract" in func_name.lower():
            return f"Extracted {return_type.lower()} data"
        elif "create" in func_name.lower() or "build" in func_name.lower():
            return f"Created {return_type} object"
        elif "validate" in func_name.lower():
            return "Validation result"
        elif "calculate" in func_name.lower() or "compute" in func_name.lower():
            return f"Calculated {return_type.lower()} result"
        elif "get" in func_name.lower() or "fetch" in func_name.lower():
            return f"Retrieved {return_type.lower()} value"
        elif "process" in func_name.lower():
            return f"Processed {return_type.lower()} result"
        else:
            return f"{return_type} result"
    
    def add_performance_attributes(self, func_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add performance-related attributes."""
        func_name = func_entry["function_name"]
        module = func_entry["module"]
        
        performance_attrs = {}
        
        # Time complexity hints
        if "sort" in func_name.lower():
            performance_attrs["time_complexity"] = "O(n log n)"
        elif "search" in func_name.lower() or "find" in func_name.lower():
            performance_attrs["time_complexity"] = "O(n)"
        elif "validate" in func_name.lower():
            performance_attrs["time_complexity"] = "O(1)"
        elif "process" in func_name.lower() and "pdf" in func_name.lower():
            performance_attrs["time_complexity"] = "O(pages)"
        elif "match" in func_name.lower():
            performance_attrs["time_complexity"] = "O(n*m)"
            
        # Memory usage hints
        if "pdf" in func_name.lower():
            performance_attrs["memory_usage"] = "High - PDF document in memory"
        elif "image" in func_name.lower():
            performance_attrs["memory_usage"] = "Medium - Image data processing"
        elif "cache" in func_name.lower():
            performance_attrs["memory_usage"] = "Variable - Depends on cache size"
        elif "validate" in func_name.lower():
            performance_attrs["memory_usage"] = "Low - Validation operations"
            
        # I/O operations
        if any(word in func_name.lower() for word in ["load", "save", "read", "write"]):
            performance_attrs["io_operations"] = "File system access"
        elif "pdf" in func_name.lower():
            performance_attrs["io_operations"] = "PDF file access"
            
        return performance_attrs
    
    def needs_enhancement(self, func_entry: Dict[str, Any]) -> bool:
        """Check if function entry needs field enhancement."""
        # Check if field_attributes is missing or empty
        field_attrs = func_entry.get("field_attributes", {})
        if not field_attrs:
            return True
            
        # Check if missing key attributes
        has_return_value = "return_value" in field_attrs
        has_parameters = any(key != "return_value" for key in field_attrs.keys())
        
        # Check if side_effects is missing or empty
        side_effects = func_entry.get("side_effects", [])
        
        # Check if dependencies is missing or empty
        dependencies = func_entry.get("dependencies", [])
        
        # Needs enhancement if missing critical fields
        return (not has_return_value and func_entry.get("return_type", "None") != "None") or \
               (not has_parameters and len(func_entry.get("parameters", [])) > 1) or \
               (not side_effects) or \
               (not dependencies)
    
    def enhance_function_entry(self, func_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance a single function entry with comprehensive field attributes."""
        if not self.needs_enhancement(func_entry):
            self.skipped_count += 1
            return func_entry
            
        # Initialize field_attributes if missing
        if "field_attributes" not in func_entry:
            func_entry["field_attributes"] = {}
            
        # Add parameter attributes
        param_info = self.analyze_function_signature(func_entry)
        func_entry["field_attributes"].update(param_info)
        
        # Add return value attributes
        if func_entry.get("return_type", "None") != "None":
            return_attrs = self.enhance_return_value_attributes(func_entry)
            if return_attrs:
                func_entry["field_attributes"]["return_value"] = return_attrs
        
        # Add performance attributes
        performance_attrs = self.add_performance_attributes(func_entry)
        if performance_attrs:
            func_entry["field_attributes"]["performance"] = performance_attrs
        
        # Enhance side_effects if missing or empty
        if not func_entry.get("side_effects"):
            func_entry["side_effects"] = self.infer_side_effects(func_entry)
        
        # Enhance dependencies if missing or empty
        if not func_entry.get("dependencies"):
            func_entry["dependencies"] = self.infer_dependencies(func_entry)
        
        # Add metadata
        func_entry["field_attributes"]["metadata"] = {
            "enhanced": True,
            "enhancement_version": "2.0",
            "last_updated": "2024-10-27"
        }
        
        self.enhanced_count += 1
        return func_entry
    
    def process_catalog(self, catalog_path: Path) -> None:
        """Process the entire function catalog."""
        if not catalog_path.exists():
            print(f"Catalog file not found: {catalog_path}")
            return
        
        # Read all functions
        functions = []
        with open(catalog_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    functions.append(json.loads(line))
        
        print(f"Processing {len(functions)} functions...")
        
        # Enhance each function
        for i, func in enumerate(functions):
            functions[i] = self.enhance_function_entry(func)
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"Processed {i + 1}/{len(functions)} functions...")
        
        print(f"Enhanced {self.enhanced_count} functions")
        print(f"Skipped {self.skipped_count} functions (already complete)")
        
        # Write back to file
        with open(catalog_path, 'w', encoding='utf-8') as f:
            for func in functions:
                f.write(json.dumps(func, separators=(',', ':')) + '\n')
        
        print(f"Updated catalog with {len(functions)} functions")

def main():
    """Main execution function."""
    enhancer = CatalogFieldEnhancer()
    catalog_path = Path("functions/function_catalog.ndjson")
    enhancer.process_catalog(catalog_path)

if __name__ == "__main__":
    main()