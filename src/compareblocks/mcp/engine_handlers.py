# src/compareblocks/mcp/engine_handlers.py

"""
MCP Engine Handlers - NEW FILE (does not modify existing engines)

Wraps existing engine implementations to expose them through MCP protocol.
This allows engines to be accessed via MCP without modifying the original engine files.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import existing engines WITHOUT modifying them
from ..engines.pymupdf_engine import PyMuPDFEngine
from ..engines.tesseract_engine import TesseractEngine
from ..engines.paddleocr_engine import PaddleOCREngine
from ..engines.docling_engine import DoclingEngine, DOCLING_AVAILABLE
from ..engines.kreuzberg_engine import KreuzbergEngine, KREUZBERG_AVAILABLE

from .protocol import MCPProtocol
from .validation import MCPValidator


class EngineHandlerMCP:
    """
    MCP handler for engine operations.
    
    Wraps existing engine implementations to provide MCP-based access
    without modifying the original engine code.
    """
    
    def __init__(self, validator: MCPValidator, protocol: MCPProtocol):
        self.validator = validator
        self.protocol = protocol
        
        # Initialize engines (using existing implementations)
        self.engines = {
            'pymupdf': PyMuPDFEngine(),
            'tesseract': TesseractEngine(),
            'paddleocr': PaddleOCREngine(),
        }
        
        # Add optional engines if available
        if DOCLING_AVAILABLE:
            self.engines['docling'] = DoclingEngine()
        
        if KREUZBERG_AVAILABLE:
            self.engines['kreuzberg'] = KreuzbergEngine()
    
    async def handle_extract_pdf(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle PDF extraction request via MCP.
        
        Args:
            params: {
                "engine": "pymupdf|tesseract|paddleocr|docling|kreuzberg",
                "pdf_path": "/path/to/file.pdf",
                "options": {...}  # Optional engine-specific options
            }
            
        Returns:
            Extraction results in standardized format
        """
        # Validate request
        required_fields = ['engine', 'pdf_path']
        for field in required_fields:
            if field not in params:
                return self.protocol.create_error_response(
                    -32602,
                    f"Missing required field: {field}"
                )
        
        engine_name = params['engine']
        pdf_path = params['pdf_path']
        options = params.get('options', {})
        
        # Validate engine exists
        if engine_name not in self.engines:
            available = ', '.join(self.engines.keys())
            return self.protocol.create_error_response(
                -32602,
                f"Unknown engine: {engine_name}. Available: {available}"
            )
        
        # Validate PDF exists
        if not Path(pdf_path).exists():
            return self.protocol.create_error_response(
                -32602,
                f"PDF file not found: {pdf_path}"
            )
        
        try:
            # Get engine
            engine = self.engines[engine_name]
            
            # Run extraction (using existing engine implementation)
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                engine.extract,
                pdf_path
            )
            
            return {
                "success": True,
                "engine": engine_name,
                "pdf_path": pdf_path,
                "result": result
            }
            
        except Exception as e:
            return self.protocol.create_error_response(
                -32603,
                f"Extraction failed: {str(e)}"
            )
    
    async def handle_list_engines(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available engines.
        
        Returns:
            List of available engines with their status
        """
        engines_info = []
        
        for name, engine in self.engines.items():
            info = {
                "name": name,
                "available": True,
                "class": engine.__class__.__name__
            }
            engines_info.append(info)
        
        # Add unavailable engines
        if not DOCLING_AVAILABLE:
            engines_info.append({
                "name": "docling",
                "available": False,
                "reason": "Package not installed"
            })
        
        if not KREUZBERG_AVAILABLE:
            engines_info.append({
                "name": "kreuzberg",
                "available": False,
                "reason": "Package not installed"
            })
        
        return {
            "success": True,
            "engines": engines_info,
            "total": len(engines_info)
        }
    
    async def handle_engine_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed information about a specific engine.
        
        Args:
            params: {"engine": "engine_name"}
            
        Returns:
            Engine details
        """
        engine_name = params.get('engine')
        
        if not engine_name:
            return self.protocol.create_error_response(
                -32602,
                "Missing required field: engine"
            )
        
        if engine_name not in self.engines:
            return self.protocol.create_error_response(
                -32602,
                f"Unknown engine: {engine_name}"
            )
        
        engine = self.engines[engine_name]
        
        return {
            "success": True,
            "engine": engine_name,
            "class": engine.__class__.__name__,
            "module": engine.__class__.__module__,
            "available": True
        }
    
    async def handle_batch_extract(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle batch extraction across multiple engines.
        
        Args:
            params: {
                "engines": ["pymupdf", "tesseract", ...],
                "pdf_path": "/path/to/file.pdf",
                "options": {...}
            }
            
        Returns:
            Results from all engines
        """
        engines_list = params.get('engines', [])
        pdf_path = params.get('pdf_path')
        
        if not pdf_path:
            return self.protocol.create_error_response(
                -32602,
                "Missing required field: pdf_path"
            )
        
        if not engines_list:
            return self.protocol.create_error_response(
                -32602,
                "Missing required field: engines"
            )
        
        # Extract with each engine
        results = {}
        errors = {}
        
        for engine_name in engines_list:
            try:
                extract_result = await self.handle_extract_pdf({
                    'engine': engine_name,
                    'pdf_path': pdf_path,
                    'options': params.get('options', {})
                })
                
                if extract_result.get('success'):
                    results[engine_name] = extract_result['result']
                else:
                    errors[engine_name] = extract_result.get('error', 'Unknown error')
                    
            except Exception as e:
                errors[engine_name] = str(e)
        
        return {
            "success": True,
            "pdf_path": pdf_path,
            "results": results,
            "errors": errors,
            "completed": len(results),
            "failed": len(errors)
        }
