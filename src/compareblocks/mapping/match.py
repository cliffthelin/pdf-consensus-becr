# src/compareblocks/mapping/match.py
"""
IoU-based matching system for mapping external variations to seed blocks.
Handles intersection-over-union calculations with configurable thresholds.
"""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from ..gbg.types import BoundingBox, SeedBlock


@dataclass
class MatchConfig:
    """Configuration for IoU-based matching."""
    exact_match_threshold: float = 0.95  # IoU threshold for exact matches
    good_match_threshold: float = 0.7    # IoU threshold for good matches
    partial_match_threshold: float = 0.3  # IoU threshold for partial matches
    min_area_overlap: float = 0.1        # Minimum area overlap to consider


@dataclass
class MatchResult:
    """Result of matching an external variation to seed blocks."""
    seed_block: Optional[SeedBlock]
    iou_score: float
    match_type: str  # "exact", "good", "partial", "no_match"
    overlap_area: float
    confidence: float


class IoUMatcher:
    """IoU-based matcher for mapping external variations to seed blocks."""
    
    def __init__(self, config: Optional[MatchConfig] = None):
        """Initialize the matcher with configuration."""
        self.config = config or MatchConfig()
    
    def calculate_iou(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes.
        
        Args:
            bbox1: First bounding box
            bbox2: Second bounding box
            
        Returns:
            IoU score between 0 and 1
        """
        # Calculate intersection coordinates
        x1_inter = max(bbox1.x, bbox2.x)
        y1_inter = max(bbox1.y, bbox2.y)
        x2_inter = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2_inter = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        # Check if there's any intersection
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        # Calculate intersection area
        intersection_area = (x2_inter - x1_inter) * (y2_inter - y1_inter)
        
        # Calculate union area
        area1 = bbox1.area()
        area2 = bbox2.area()
        union_area = area1 + area2 - intersection_area
        
        # Avoid division by zero
        if union_area == 0:
            return 0.0
        
        return intersection_area / union_area
    
    def calculate_overlap_area(self, bbox1: BoundingBox, bbox2: BoundingBox) -> float:
        """
        Calculate the overlap area between two bounding boxes.
        
        Args:
            bbox1: First bounding box
            bbox2: Second bounding box
            
        Returns:
            Overlap area
        """
        # Calculate intersection coordinates
        x1_inter = max(bbox1.x, bbox2.x)
        y1_inter = max(bbox1.y, bbox2.y)
        x2_inter = min(bbox1.x + bbox1.width, bbox2.x + bbox2.width)
        y2_inter = min(bbox1.y + bbox1.height, bbox2.y + bbox2.height)
        
        # Check if there's any intersection
        if x2_inter <= x1_inter or y2_inter <= y1_inter:
            return 0.0
        
        return (x2_inter - x1_inter) * (y2_inter - y1_inter)
    
    def match_to_seed_blocks(
        self, 
        external_bbox: BoundingBox, 
        seed_blocks: List[SeedBlock],
        page_filter: Optional[int] = None
    ) -> List[MatchResult]:
        """
        Match an external bounding box to seed blocks using IoU.
        
        Args:
            external_bbox: Bounding box from external extraction
            seed_blocks: List of seed blocks to match against
            page_filter: Optional page number to filter seed blocks
            
        Returns:
            List of match results sorted by IoU score (descending)
        """
        matches = []
        
        for seed_block in seed_blocks:
            # Filter by page if specified
            if page_filter is not None and seed_block.page != page_filter:
                continue
            
            # Calculate IoU and overlap
            iou_score = self.calculate_iou(external_bbox, seed_block.bbox)
            overlap_area = self.calculate_overlap_area(external_bbox, seed_block.bbox)
            
            # Skip if below minimum area overlap
            if overlap_area < self.config.min_area_overlap:
                continue
            
            # Determine match type based on IoU thresholds
            if iou_score >= self.config.exact_match_threshold:
                match_type = "exact"
                confidence = 1.0
            elif iou_score >= self.config.good_match_threshold:
                match_type = "good"
                confidence = 0.8
            elif iou_score >= self.config.partial_match_threshold:
                match_type = "partial"
                confidence = 0.5
            else:
                match_type = "no_match"
                confidence = 0.1
            
            matches.append(MatchResult(
                seed_block=seed_block,
                iou_score=iou_score,
                match_type=match_type,
                overlap_area=overlap_area,
                confidence=confidence
            ))
        
        # Sort by IoU score descending
        matches.sort(key=lambda x: x.iou_score, reverse=True)
        return matches
    
    def find_best_match(
        self, 
        external_bbox: BoundingBox, 
        seed_blocks: List[SeedBlock],
        page_filter: Optional[int] = None
    ) -> Optional[MatchResult]:
        """
        Find the best matching seed block for an external bounding box.
        
        Args:
            external_bbox: Bounding box from external extraction
            seed_blocks: List of seed blocks to match against
            page_filter: Optional page number to filter seed blocks
            
        Returns:
            Best match result or None if no good match found
        """
        matches = self.match_to_seed_blocks(external_bbox, seed_blocks, page_filter)
        
        if not matches:
            return None
        
        best_match = matches[0]
        
        # Only return matches that meet minimum quality threshold
        if best_match.match_type == "no_match":
            return None
        
        return best_match
    
    def handle_exact_matches(
        self, 
        external_bbox: BoundingBox, 
        seed_blocks: List[SeedBlock],
        page_filter: Optional[int] = None
    ) -> List[MatchResult]:
        """
        Handle exact matches and slightly larger/smaller bounding boxes.
        
        Args:
            external_bbox: Bounding box from external extraction
            seed_blocks: List of seed blocks to match against
            page_filter: Optional page number to filter seed blocks
            
        Returns:
            List of exact or near-exact matches
        """
        matches = self.match_to_seed_blocks(external_bbox, seed_blocks, page_filter)
        
        # Filter for exact and good matches only
        exact_matches = [
            match for match in matches 
            if match.match_type in ["exact", "good"]
        ]
        
        return exact_matches
    
    def get_match_statistics(
        self, 
        external_bboxes: List[BoundingBox], 
        seed_blocks: List[SeedBlock]
    ) -> Dict[str, Any]:
        """
        Get statistics about matching performance across multiple external boxes.
        
        Args:
            external_bboxes: List of external bounding boxes
            seed_blocks: List of seed blocks
            
        Returns:
            Dictionary with matching statistics
        """
        stats = {
            "total_external": len(external_bboxes),
            "exact_matches": 0,
            "good_matches": 0,
            "partial_matches": 0,
            "no_matches": 0,
            "avg_iou": 0.0,
            "match_rate": 0.0
        }
        
        total_iou = 0.0
        matched_count = 0
        
        for bbox in external_bboxes:
            best_match = self.find_best_match(bbox, seed_blocks)
            
            if best_match:
                matched_count += 1
                total_iou += best_match.iou_score
                
                if best_match.match_type == "exact":
                    stats["exact_matches"] += 1
                elif best_match.match_type == "good":
                    stats["good_matches"] += 1
                elif best_match.match_type == "partial":
                    stats["partial_matches"] += 1
            else:
                stats["no_matches"] += 1
        
        if matched_count > 0:
            stats["avg_iou"] = total_iou / matched_count
            stats["match_rate"] = matched_count / len(external_bboxes)
        
        return stats