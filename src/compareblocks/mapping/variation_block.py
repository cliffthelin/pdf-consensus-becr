# src/compareblocks/mapping/variation_block.py
"""
Variation block management system for handling multiple engine outputs.
Creates child variation blocks for partial matches and overlapping regions.
"""

from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from ..gbg.types import BoundingBox, SeedBlock, OrientationHints
from .match import IoUMatcher, MatchResult, MatchConfig


class VariationType(Enum):
    """Types of variation blocks."""
    SEED = "seed"           # Original seed block from GBG
    EXTERNAL = "external"   # External variation mapped to seed
    CHILD = "child"         # Child variation for partial matches
    ORPHAN = "orphan"       # Unmatched external variation


@dataclass
class VariationBlock:
    """Represents a text variation block from any engine."""
    
    # Core identification
    variation_id: str
    doc_id: str
    page: int
    raw_text: str
    engine: str
    bbox: BoundingBox
    
    # Optional fields with defaults
    block_id: Optional[str] = None  # Seed block ID if mapped
    confidence: float = 0.0
    orientation: Optional[float] = None
    
    # Variation metadata
    variation_type: VariationType = VariationType.EXTERNAL
    parent_block_id: Optional[str] = None  # For child variations
    child_blocks: List[str] = field(default_factory=list)  # Child variation IDs
    
    # Original metadata preservation
    original_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Mapping information
    mapping_confidence: float = 0.0
    iou_score: float = 0.0
    match_type: str = "unknown"
    
    def __post_init__(self):
        """Validate variation block data."""
        if self.page < 0:
            raise ValueError("Page number must be non-negative")
        if not self.doc_id:
            raise ValueError("Document ID cannot be empty")
        if not self.engine:
            raise ValueError("Engine name cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        if not 0.0 <= self.mapping_confidence <= 1.0:
            raise ValueError("Mapping confidence must be between 0 and 1")
    
    def is_mapped(self) -> bool:
        """Check if this variation is mapped to a seed block."""
        return self.block_id is not None
    
    def is_child_variation(self) -> bool:
        """Check if this is a child variation block."""
        return self.variation_type == VariationType.CHILD
    
    def is_orphan(self) -> bool:
        """Check if this is an orphaned (unmatched) variation."""
        return self.variation_type == VariationType.ORPHAN
    
    def add_child(self, child_variation_id: str):
        """Add a child variation to this block."""
        if child_variation_id not in self.child_blocks:
            self.child_blocks.append(child_variation_id)
    
    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get a value from original metadata."""
        return self.original_metadata.get(key, default)


@dataclass
class ExternalVariation:
    """Represents an external variation before mapping."""
    doc_id: str
    page: int
    engine: str
    raw_text: str
    bbox: BoundingBox
    confidence: float = 0.0
    orientation: Optional[float] = None
    block_id: Optional[str] = None  # If provided by external engine
    metadata: Dict[str, Any] = field(default_factory=dict)


class VariationBlockManager:
    """Manages variation blocks and handles mapping to seed blocks."""
    
    def __init__(self, match_config: Optional[MatchConfig] = None):
        """Initialize the variation block manager."""
        self.matcher = IoUMatcher(match_config)
        self.variation_blocks: Dict[str, VariationBlock] = {}
        self.seed_blocks: Dict[str, SeedBlock] = {}
        self._next_variation_id = 1
    
    def _generate_variation_id(self) -> str:
        """Generate a unique variation ID."""
        var_id = f"var_{self._next_variation_id:06d}"
        self._next_variation_id += 1
        return var_id
    
    def add_seed_blocks(self, seed_blocks: List[SeedBlock]):
        """Add seed blocks to the manager."""
        for seed_block in seed_blocks:
            self.seed_blocks[seed_block.block_id] = seed_block
            
            # Create a variation block for the seed
            variation_id = self._generate_variation_id()
            seed_variation = VariationBlock(
                variation_id=variation_id,
                block_id=seed_block.block_id,
                doc_id=f"seed_{seed_block.page}",  # Placeholder doc_id
                page=seed_block.page,
                raw_text=seed_block.text_content or "",
                engine="seed_gbg",
                confidence=1.0,
                bbox=seed_block.bbox,
                variation_type=VariationType.SEED,
                mapping_confidence=1.0,
                iou_score=1.0,
                match_type="exact",
                original_metadata=seed_block.metadata or {}
            )
            self.variation_blocks[variation_id] = seed_variation
    
    def map_external_variation(self, external_var: ExternalVariation) -> VariationBlock:
        """
        Map an external variation to seed blocks and create variation block.
        
        Args:
            external_var: External variation to map
            
        Returns:
            Created variation block
        """
        variation_id = self._generate_variation_id()
        
        # If external variation already has a block_id, try to use it
        if external_var.block_id and external_var.block_id in self.seed_blocks:
            seed_block = self.seed_blocks[external_var.block_id]
            variation_block = VariationBlock(
                variation_id=variation_id,
                block_id=external_var.block_id,
                doc_id=external_var.doc_id,
                page=external_var.page,
                raw_text=external_var.raw_text,
                engine=external_var.engine,
                confidence=external_var.confidence,
                bbox=external_var.bbox,
                orientation=external_var.orientation,
                variation_type=VariationType.EXTERNAL,
                mapping_confidence=1.0,
                iou_score=1.0,
                match_type="exact",
                original_metadata=external_var.metadata
            )
        else:
            # Find best match using IoU
            seed_blocks_list = list(self.seed_blocks.values())
            best_match = self.matcher.find_best_match(
                external_var.bbox, 
                seed_blocks_list, 
                page_filter=external_var.page
            )
            
            if best_match and best_match.match_type in ["exact", "good"]:
                # Map to existing seed block
                variation_block = VariationBlock(
                    variation_id=variation_id,
                    block_id=best_match.seed_block.block_id,
                    doc_id=external_var.doc_id,
                    page=external_var.page,
                    raw_text=external_var.raw_text,
                    engine=external_var.engine,
                    confidence=external_var.confidence,
                    bbox=external_var.bbox,
                    orientation=external_var.orientation,
                    variation_type=VariationType.EXTERNAL,
                    mapping_confidence=best_match.confidence,
                    iou_score=best_match.iou_score,
                    match_type=best_match.match_type,
                    original_metadata=external_var.metadata
                )
            elif best_match and best_match.match_type == "partial":
                # Create child variation for partial match
                variation_block = VariationBlock(
                    variation_id=variation_id,
                    block_id=None,  # Child blocks don't have direct block_id
                    doc_id=external_var.doc_id,
                    page=external_var.page,
                    raw_text=external_var.raw_text,
                    engine=external_var.engine,
                    confidence=external_var.confidence,
                    bbox=external_var.bbox,
                    orientation=external_var.orientation,
                    variation_type=VariationType.CHILD,
                    parent_block_id=best_match.seed_block.block_id,
                    mapping_confidence=best_match.confidence,
                    iou_score=best_match.iou_score,
                    match_type=best_match.match_type,
                    original_metadata=external_var.metadata
                )
                
                # Add this as a child to the parent seed block variation
                parent_variations = self.get_variations_for_block(best_match.seed_block.block_id)
                for parent_var in parent_variations:
                    if parent_var.variation_type == VariationType.SEED:
                        parent_var.add_child(variation_id)
                        break
            else:
                # Create orphan variation
                variation_block = VariationBlock(
                    variation_id=variation_id,
                    block_id=None,
                    doc_id=external_var.doc_id,
                    page=external_var.page,
                    raw_text=external_var.raw_text,
                    engine=external_var.engine,
                    confidence=external_var.confidence,
                    bbox=external_var.bbox,
                    orientation=external_var.orientation,
                    variation_type=VariationType.ORPHAN,
                    mapping_confidence=0.0,
                    iou_score=0.0,
                    match_type="no_match",
                    original_metadata=external_var.metadata
                )
        
        self.variation_blocks[variation_id] = variation_block
        return variation_block
    
    def get_variations_for_block(self, block_id: str) -> List[VariationBlock]:
        """Get all variations mapped to a specific seed block."""
        variations = []
        for variation in self.variation_blocks.values():
            if variation.block_id == block_id:
                variations.append(variation)
        return variations
    
    def get_child_variations(self, parent_block_id: str) -> List[VariationBlock]:
        """Get all child variations for a parent block."""
        children = []
        for variation in self.variation_blocks.values():
            if (variation.variation_type == VariationType.CHILD and 
                variation.parent_block_id == parent_block_id):
                children.append(variation)
        return children
    
    def get_orphan_variations(self) -> List[VariationBlock]:
        """Get all orphaned (unmatched) variations."""
        orphans = []
        for variation in self.variation_blocks.values():
            if variation.variation_type == VariationType.ORPHAN:
                orphans.append(variation)
        return orphans
    
    def get_variations_by_page(self, page: int) -> List[VariationBlock]:
        """Get all variations for a specific page."""
        page_variations = []
        for variation in self.variation_blocks.values():
            if variation.page == page:
                page_variations.append(variation)
        return page_variations
    
    def get_variations_by_engine(self, engine: str) -> List[VariationBlock]:
        """Get all variations from a specific engine."""
        engine_variations = []
        for variation in self.variation_blocks.values():
            if variation.engine == engine:
                engine_variations.append(variation)
        return engine_variations
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get statistics about variation mapping."""
        stats = {
            "total_variations": len(self.variation_blocks),
            "seed_variations": 0,
            "external_variations": 0,
            "child_variations": 0,
            "orphan_variations": 0,
            "mapped_variations": 0,
            "mapping_rate": 0.0,
            "avg_iou": 0.0,
            "engines": set()
        }
        
        total_iou = 0.0
        iou_count = 0
        
        for variation in self.variation_blocks.values():
            stats["engines"].add(variation.engine)
            
            if variation.variation_type == VariationType.SEED:
                stats["seed_variations"] += 1
            elif variation.variation_type == VariationType.EXTERNAL:
                stats["external_variations"] += 1
            elif variation.variation_type == VariationType.CHILD:
                stats["child_variations"] += 1
            elif variation.variation_type == VariationType.ORPHAN:
                stats["orphan_variations"] += 1
            
            if variation.is_mapped():
                stats["mapped_variations"] += 1
            
            if variation.iou_score > 0:
                total_iou += variation.iou_score
                iou_count += 1
        
        if iou_count > 0:
            stats["avg_iou"] = total_iou / iou_count
        
        non_seed_variations = stats["total_variations"] - stats["seed_variations"]
        if non_seed_variations > 0:
            # Only count non-seed mapped variations for mapping rate
            non_seed_mapped = stats["mapped_variations"] - stats["seed_variations"]
            stats["mapping_rate"] = non_seed_mapped / non_seed_variations
        
        stats["engines"] = list(stats["engines"])
        return stats
    
    def create_overlapping_regions(
        self, 
        variations: List[VariationBlock]
    ) -> List[VariationBlock]:
        """
        Create child variation blocks for overlapping regions.
        
        Args:
            variations: List of variations to analyze for overlaps
            
        Returns:
            List of new child variation blocks for overlapping regions
        """
        child_variations = []
        
        # Group variations by page
        page_groups = {}
        for variation in variations:
            if variation.page not in page_groups:
                page_groups[variation.page] = []
            page_groups[variation.page].append(variation)
        
        # Find overlaps within each page
        for page, page_variations in page_groups.items():
            for i, var1 in enumerate(page_variations):
                for j, var2 in enumerate(page_variations[i+1:], i+1):
                    # Calculate overlap
                    overlap_area = self.matcher.calculate_overlap_area(var1.bbox, var2.bbox)
                    
                    if overlap_area > 0:
                        # Create child variation for overlapping region
                        child_id = self._generate_variation_id()
                        
                        # Calculate overlapping bounding box
                        x1 = max(var1.bbox.x, var2.bbox.x)
                        y1 = max(var1.bbox.y, var2.bbox.y)
                        x2 = min(var1.bbox.x + var1.bbox.width, var2.bbox.x + var2.bbox.width)
                        y2 = min(var1.bbox.y + var1.bbox.height, var2.bbox.y + var2.bbox.height)
                        
                        overlap_bbox = BoundingBox(x=x1, y=y1, width=x2-x1, height=y2-y1)
                        
                        child_variation = VariationBlock(
                            variation_id=child_id,
                            block_id=None,
                            doc_id=var1.doc_id,
                            page=page,
                            raw_text=f"OVERLAP: {var1.engine} + {var2.engine}",
                            engine="overlap_detector",
                            confidence=min(var1.confidence, var2.confidence),
                            bbox=overlap_bbox,
                            variation_type=VariationType.CHILD,
                            parent_block_id=var1.block_id or var2.block_id,
                            mapping_confidence=0.5,
                            iou_score=overlap_area / min(var1.bbox.area(), var2.bbox.area()),
                            match_type="overlap",
                            original_metadata={
                                "overlap_engines": [var1.engine, var2.engine],
                                "overlap_area": overlap_area,
                                "parent_variations": [var1.variation_id, var2.variation_id]
                            }
                        )
                        
                        child_variations.append(child_variation)
                        self.variation_blocks[child_id] = child_variation
        
        return child_variations