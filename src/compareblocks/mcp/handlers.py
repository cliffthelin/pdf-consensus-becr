# src/compareblocks/mcp/handlers.py

"""
MCP request handlers for BECR system.

Provides handlers for different types of MCP requests including extraction
submission, status monitoring, and result retrieval.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .validation import MCPValidator
from .protocol import MCPMessage, MCPProtocol, MCPErrorCode
from ..io.loader import NDJSONLoader
from ..io.writer import NDJSONWriter
from ..gbg.processor import GBGProcessor
from ..consensus.score import ConsensusScorer
from ..config.file_manager import FileManager


class ProcessingSession:
    """Represents a processing session."""
    
    def __init__(self, session_id: str, pdf_path: str, metadata: Dict[str, Any]):
        self.session_id = session_id
        self.pdf_path = pdf_path
        self.metadata = metadata
        self.status = "initialized"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.progress = 0.0
        self.results: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.variations: List[Dict[str, Any]] = []
    
    def update_status(self, status: str, progress: float = None, error: str = None):
        """Update session status."""
        self.status = status
        self.updated_at = datetime.now()
        if progress is not None:
            self.progress = progress
        if error is not None:
            self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "pdf_path": self.pdf_path,
            "metadata": self.metadata,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "error": self.error,
            "variation_count": len(self.variations)
        }


class ExtractionHandler:
    """Handler for extraction submission requests."""
    
    def __init__(self, validator: MCPValidator, protocol: MCPProtocol):
        self.validator = validator
        self.protocol = protocol
        self.sessions: Dict[str, ProcessingSession] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.config_manager = FileManager()
    
    async def handle_submission(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle extraction submission request."""
        # Validate submission data
        is_valid, error_msg = self.validator.validate_extraction_submission(params)
        if not is_valid:
            raise ValueError(f"Invalid extraction submission: {error_msg}")
        
        # Sanitize data
        sanitized_data = self.validator.sanitize_extraction_data(params)
        
        # Validate PDF path
        pdf_path = sanitized_data["pdf_path"]
        is_valid_path, path_error = self.validator.validate_pdf_path(pdf_path)
        if not is_valid_path:
            raise ValueError(f"Invalid PDF path: {path_error}")
        
        # Create processing session
        session_id = str(uuid.uuid4())
        session = ProcessingSession(
            session_id=session_id,
            pdf_path=pdf_path,
            metadata=sanitized_data.get("metadata", {})
        )
        session.variations = sanitized_data["variations"]
        self.sessions[session_id] = session
        
        # Start processing asynchronously
        asyncio.create_task(self._process_extraction(session))
        
        return {
            "session_id": session_id,
            "status": "accepted",
            "message": "Extraction submission accepted for processing"
        }
    
    async def _process_extraction(self, session: ProcessingSession):
        """Process extraction in background."""
        try:
            session.update_status("processing", 0.1)
            
            # Notify subscribers of status update
            await self._notify_status_update(session)
            
            # Initialize processors
            gbg_processor = GBGProcessor()
            consensus_scorer = ConsensusScorer()
            
            # Process PDF with GBG
            session.update_status("processing", 0.3)
            pdf_path = Path(session.pdf_path)
            gbg_results = gbg_processor.process_pdf(str(pdf_path))
            
            # Extract seed blocks from GBG results
            seed_blocks = []
            for page_data in gbg_results.get("pages", {}).values():
                if isinstance(page_data, dict) and "blocks" in page_data:
                    seed_blocks.extend(page_data["blocks"])
            
            # Map variations to blocks
            session.update_status("processing", 0.5)
            mapped_variations = self._map_variations_to_blocks(
                session.variations, seed_blocks
            )
            
            # Run consensus scoring
            session.update_status("processing", 0.7)
            consensus_results = consensus_scorer.score_variations(mapped_variations)
            
            # Generate final results
            session.update_status("processing", 0.9)
            results = self._generate_results(consensus_results, session.metadata)
            
            # Complete processing
            session.results = results
            session.update_status("completed", 1.0)
            
            # Notify subscribers of completion
            await self._notify_processing_complete(session)
            
        except Exception as e:
            session.update_status("error", error=str(e))
            await self._notify_error(session, str(e))
    
    def _map_variations_to_blocks(self, variations: List[Dict[str, Any]], 
                                 seed_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map external variations to seed blocks."""
        # This would use the existing mapping logic from the system
        # For now, return a simplified mapping
        mapped = []
        for variation in variations:
            # Find best matching seed block based on bounding box
            best_match = None
            best_iou = 0.0
            
            var_bbox = variation.get("bbox", {})
            for block in seed_blocks:
                block_bbox = block.get("bbox", {})
                iou = self._calculate_iou(var_bbox, block_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_match = block
            
            if best_match and best_iou > 0.5:  # Minimum IoU threshold
                mapped_variation = variation.copy()
                mapped_variation["block_id"] = best_match["block_id"]
                mapped_variation["iou_score"] = best_iou
                mapped.append(mapped_variation)
        
        return mapped
    
    def _calculate_iou(self, bbox1, bbox2) -> float:
        """Calculate Intersection over Union for two bounding boxes."""
        # Convert array format [x, y, width, height] to dict format if needed
        def normalize_bbox(bbox):
            if isinstance(bbox, list) and len(bbox) == 4:
                return {"x": bbox[0], "y": bbox[1], "width": bbox[2], "height": bbox[3]}
            elif isinstance(bbox, dict):
                return bbox
            else:
                return {}
        
        bbox1 = normalize_bbox(bbox1)
        bbox2 = normalize_bbox(bbox2)
        
        if not all(k in bbox1 for k in ["x", "y", "width", "height"]):
            return 0.0
        if not all(k in bbox2 for k in ["x", "y", "width", "height"]):
            return 0.0
        
        # Calculate intersection
        x1 = max(bbox1["x"], bbox2["x"])
        y1 = max(bbox1["y"], bbox2["y"])
        x2 = min(bbox1["x"] + bbox1["width"], bbox2["x"] + bbox2["width"])
        y2 = min(bbox1["y"] + bbox1["height"], bbox2["y"] + bbox2["height"])
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        intersection = (x2 - x1) * (y2 - y1)
        
        # Calculate union
        area1 = bbox1["width"] * bbox1["height"]
        area2 = bbox2["width"] * bbox2["height"]
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_results(self, consensus_results: List[Dict[str, Any]], 
                         metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final processing results."""
        return {
            "consensus_decisions": consensus_results,
            "metadata": metadata,
            "processing_timestamp": datetime.now().isoformat(),
            "total_blocks": len(consensus_results),
            "statistics": {
                "auto_selected": sum(1 for r in consensus_results if r.get("decision_reason") == "auto_select"),
                "manual_review": sum(1 for r in consensus_results if r.get("decision_reason") == "manual_review"),
                "merged": sum(1 for r in consensus_results if r.get("decision_reason") == "merged")
            }
        }
    
    async def _notify_status_update(self, session: ProcessingSession):
        """Notify subscribers of status update."""
        notification = self.protocol.create_status_update(session.to_dict())
        # In a real implementation, this would send to actual subscribers
        print(f"Status update notification: {notification.to_json()}")
    
    async def _notify_processing_complete(self, session: ProcessingSession):
        """Notify subscribers of processing completion."""
        notification = self.protocol.create_processing_complete({
            "session_id": session.session_id,
            "results": session.results
        })
        print(f"Processing complete notification: {notification.to_json()}")
    
    async def _notify_error(self, session: ProcessingSession, error: str):
        """Notify subscribers of processing error."""
        notification = self.protocol.create_notification(
            method="processing_error",
            params={
                "session_id": session.session_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )
        print(f"Error notification: {notification.to_json()}")
    
    def get_session(self, session_id: str) -> Optional[ProcessingSession]:
        """Get processing session by ID."""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[ProcessingSession]:
        """List all processing sessions."""
        return list(self.sessions.values())


class StatusHandler:
    """Handler for status monitoring requests."""
    
    def __init__(self, extraction_handler: ExtractionHandler):
        self.extraction_handler = extraction_handler
    
    def handle_status_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status request."""
        session_id = params.get("session_id")
        include_details = params.get("include_details", False)
        
        if session_id:
            # Get specific session status
            session = self.extraction_handler.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            status_data = session.to_dict()
            if include_details and session.results:
                status_data["results_summary"] = {
                    "total_blocks": len(session.results.get("consensus_decisions", [])),
                    "statistics": session.results.get("statistics", {})
                }
            
            return status_data
        else:
            # Get overall system status
            sessions = self.extraction_handler.list_sessions()
            return {
                "system_status": "operational",
                "total_sessions": len(sessions),
                "active_sessions": len([s for s in sessions if s.status == "processing"]),
                "completed_sessions": len([s for s in sessions if s.status == "completed"]),
                "error_sessions": len([s for s in sessions if s.status == "error"]),
                "timestamp": datetime.now().isoformat()
            }
    
    def handle_results_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle results retrieval request."""
        session_id = params["session_id"]
        format_type = params.get("format", "json")
        include_analytics = params.get("include_analytics", False)
        
        session = self.extraction_handler.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        if session.status != "completed":
            raise ValueError(f"Session not completed: {session.status}")
        
        if not session.results:
            raise ValueError("No results available")
        
        results = session.results.copy()
        
        if include_analytics:
            results["analytics"] = self._generate_analytics(session)
        
        if format_type == "ndjson":
            # Convert to NDJSON format
            ndjson_lines = []
            for decision in results["consensus_decisions"]:
                ndjson_lines.append(json.dumps(decision))
            results["ndjson_data"] = "\n".join(ndjson_lines)
        elif format_type == "summary":
            # Return only summary information
            results = {
                "session_id": session_id,
                "statistics": results.get("statistics", {}),
                "processing_timestamp": results.get("processing_timestamp"),
                "total_blocks": results.get("total_blocks", 0)
            }
        
        return results
    
    def _generate_analytics(self, session: ProcessingSession) -> Dict[str, Any]:
        """Generate analytics for session results."""
        if not session.results:
            return {}
        
        decisions = session.results.get("consensus_decisions", [])
        
        # Calculate quality metrics
        confidence_scores = [d.get("consensus_score", 0) for d in decisions]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        # Engine performance
        engine_stats = {}
        for decision in decisions:
            selected_engine = decision.get("selected_engine")
            if selected_engine:
                if selected_engine not in engine_stats:
                    engine_stats[selected_engine] = {"count": 0, "total_score": 0}
                engine_stats[selected_engine]["count"] += 1
                engine_stats[selected_engine]["total_score"] += decision.get("consensus_score", 0)
        
        # Calculate average scores per engine
        for engine, stats in engine_stats.items():
            stats["avg_score"] = stats["total_score"] / stats["count"] if stats["count"] > 0 else 0
        
        return {
            "quality_metrics": {
                "average_confidence": avg_confidence,
                "high_confidence_blocks": len([s for s in confidence_scores if s > 0.8]),
                "low_confidence_blocks": len([s for s in confidence_scores if s < 0.5])
            },
            "engine_performance": engine_stats,
            "processing_time": (session.updated_at - session.created_at).total_seconds(),
            "variation_count": len(session.variations)
        }