# src/compareblocks/features/consistency_integration.py
"""
Integration module for character consistency tracking with association management.
Provides dynamic consistency updates when new associated files are added.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from .consistency import (
    CharacterConsistencyTracker, CharacterConsistency, 
    ConsistencyOverrideManager, calculate_dynamic_consistency_percentage
)
from ..association.manager import AssociationManager, PDFAssociations


@dataclass
class BlockConsistencyState:
    """State tracking for block consistency across associated files."""
    block_id: str
    pdf_path: str
    current_consistency: CharacterConsistency
    associated_files: List[str]
    last_updated: str
    version: int = 1


class ConsistencyIntegrationManager:
    """Manages integration between consistency tracking and association management."""
    
    def __init__(self):
        """Initialize the integration manager."""
        self.consistency_tracker = CharacterConsistencyTracker()
        self.override_manager = ConsistencyOverrideManager()
        self.association_manager = AssociationManager()
        self.block_states: Dict[str, BlockConsistencyState] = {}
        
        # Add default education-specific override terms
        self._setup_default_overrides()
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_default_overrides(self) -> None:
        """Set up default override terms for education domain."""
        education_acronyms = [
            'ELA', 'STEM', 'IEP', 'IDEA', 'NCLB', 'ESSA', 'RTI', 'PBIS',
            'SEL', 'CCSS', 'NGSS', 'AP', 'IB', 'SAT', 'ACT', 'GPA'
        ]
        
        education_terms = [
            'phonics', 'comprehension', 'literacy', 'numeracy', 'pedagogy',
            'curriculum', 'assessment', 'rubric', 'scaffolding', 'differentiation'
        ]
        
        self.override_manager.add_acronyms(education_acronyms)
        self.override_manager.add_domain_terms(education_terms)
        
        # Pass override terms to consistency tracker
        all_override_terms = list(self.override_manager.get_all_override_terms())
        self.consistency_tracker.add_override_terms(all_override_terms)
    
    def track_block_consistency_with_associations(self, pdf_path: str, block_id: str, 
                                                block_variations: List[str],
                                                block_position: Optional[int] = None) -> CharacterConsistency:
        """
        Track block consistency including all associated files for the PDF.
        Focuses on block-level comparisons across different extraction sources.
        
        Args:
            pdf_path: Path to the PDF file
            block_id: Unique identifier for the block
            block_variations: Text variations for this specific block from different engines
            block_position: Optional position of block in document for context
            
        Returns:
            CharacterConsistency object with comprehensive metrics
        """
        # Load associations for the PDF
        associations = self.association_manager.load_associations_for_pdf(pdf_path)
        
        # Start with provided block variations (from different OCR engines)
        all_block_variations = list(block_variations)
        
        # Add block-level content from associated files
        # This should map to the same logical block across different extraction methods
        for file_path, parsed_content in associations.associations.items():
            if parsed_content.text_content:
                # In a real implementation, we would need to:
                # 1. Map the block_id to corresponding content in each associated file
                # 2. Extract the equivalent text block from each file
                # For now, we simulate this by taking a representative portion
                
                # Extract block-equivalent content (this is simplified)
                block_equivalent = self._extract_block_equivalent_content(
                    parsed_content.text_content, block_position
                )
                if block_equivalent:
                    all_block_variations.append(block_equivalent)
        
        # Track consistency with all block-level variations
        consistency = self.consistency_tracker.track_consistency_for_block(
            block_id, all_block_variations
        )
        
        # Store state for future updates
        self.block_states[block_id] = BlockConsistencyState(
            block_id=block_id,
            pdf_path=pdf_path,
            current_consistency=consistency,
            associated_files=list(associations.associations.keys()),
            last_updated=associations.last_updated.isoformat(),
            version=1
        )
        
        return consistency
    
    def _extract_block_equivalent_content(self, full_text: str, block_position: Optional[int]) -> Optional[str]:
        """
        Extract block-equivalent content from full text based on position.
        This is a simplified implementation - in practice, this would use
        more sophisticated block mapping algorithms.
        
        Args:
            full_text: Full text content from associated file
            block_position: Position of the block in the document
            
        Returns:
            Block-equivalent text content or None
        """
        if not full_text or block_position is None:
            return None
        
        # Simple approach: split into sentences and take the one at block_position
        sentences = [s.strip() for s in full_text.split('.') if s.strip()]
        
        if block_position < len(sentences):
            return sentences[block_position]
        
        return None
    
    def track_block_consistency_with_surrounding_context(self, pdf_path: str, block_id: str,
                                                       block_variations: List[str],
                                                       surrounding_blocks: Optional[Dict[str, Dict[str, List[str]]]] = None) -> CharacterConsistency:
        """
        Track block consistency with surrounding block context when needed.
        
        Args:
            pdf_path: Path to the PDF file
            block_id: Unique identifier for the block
            block_variations: Text variations for this block
            surrounding_blocks: Optional dict with 'before' and 'after' block variations
                              Format: {'before': {'block_id': [variations]}, 'after': {'block_id': [variations]}}
            
        Returns:
            CharacterConsistency object with context-aware metrics
        """
        # Prepare surrounding context if provided
        context_blocks = None
        if surrounding_blocks:
            context_blocks = {}
            
            # Extract before context
            if 'before' in surrounding_blocks and surrounding_blocks['before']:
                before_variations = []
                for before_block_id, variations in surrounding_blocks['before'].items():
                    if variations:
                        before_variations.extend(variations)
                if before_variations:
                    context_blocks['before'] = before_variations
            
            # Extract after context
            if 'after' in surrounding_blocks and surrounding_blocks['after']:
                after_variations = []
                for after_block_id, variations in surrounding_blocks['after'].items():
                    if variations:
                        after_variations.extend(variations)
                if after_variations:
                    context_blocks['after'] = after_variations
        
        # Track consistency with context
        consistency = self.consistency_tracker.track_consistency_for_block_with_context(
            block_id, block_variations, context_blocks
        )
        
        # Store state
        self.block_states[block_id] = BlockConsistencyState(
            block_id=block_id,
            pdf_path=pdf_path,
            current_consistency=consistency,
            associated_files=[],  # No associated files in this context
            last_updated="",
            version=1
        )
        
        return consistency
    
    def update_consistency_with_new_association(self, pdf_path: str, block_id: str, 
                                              new_file_path: str) -> CharacterConsistency:
        """
        Update block consistency when a new associated file is added.
        
        Args:
            pdf_path: Path to the PDF file
            block_id: Block identifier
            new_file_path: Path to the new associated file
            
        Returns:
            Updated CharacterConsistency object
        """
        # Refresh associations to include new file
        associations = self.association_manager.refresh_associations(pdf_path)
        
        # Get current state
        current_state = self.block_states.get(block_id)
        if not current_state:
            self.logger.warning(f"No existing state for block {block_id}, creating new")
            # Create new state with empty variations
            return self.track_block_consistency_with_associations(pdf_path, block_id, [])
        
        # Collect all variations including new file
        all_variations = []
        
        # Add content from all associated files
        for file_path, parsed_content in associations.associations.items():
            if parsed_content.text_content:
                all_variations.append(parsed_content.text_content[:200])
        
        # Update consistency
        updated_consistency = self.consistency_tracker.update_consistency_with_new_files(
            current_state.current_consistency, all_variations
        )
        
        # Update state
        self.block_states[block_id] = BlockConsistencyState(
            block_id=block_id,
            pdf_path=pdf_path,
            current_consistency=updated_consistency,
            associated_files=list(associations.associations.keys()),
            last_updated=associations.last_updated.isoformat(),
            version=current_state.version + 1
        )
        
        return updated_consistency
    
    def get_dynamic_consistency_percentages(self, pdf_path: str) -> Dict[str, float]:
        """
        Get dynamic consistency percentages for all blocks in a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with overall consistency metrics
        """
        # Get all block states for this PDF
        pdf_blocks = [
            state.current_consistency 
            for state in self.block_states.values() 
            if state.pdf_path == pdf_path
        ]
        
        if not pdf_blocks:
            return {
                'overall_character_consistency': 1.0,
                'overall_word_consistency': 1.0,
                'overall_spelling_accuracy': 1.0,
                'total_blocks': 0
            }
        
        return calculate_dynamic_consistency_percentage(pdf_blocks)
    
    def apply_consistency_overrides(self, block_id: str, override_terms: List[str]) -> None:
        """
        Apply consistency overrides for specific terms in a block.
        
        Args:
            block_id: Block identifier
            override_terms: List of terms to override
        """
        self.override_manager.add_custom_overrides(override_terms)
        
        # Update consistency tracker with new overrides
        all_override_terms = list(self.override_manager.get_all_override_terms())
        self.consistency_tracker.add_override_terms(all_override_terms)
        
        # If we have existing state for this block, mark it for recalculation
        if block_id in self.block_states:
            state = self.block_states[block_id]
            # In a full implementation, we'd recalculate consistency here
            self.logger.info(f"Override terms applied to block {block_id}, recalculation needed")
    
    def get_consistency_summary_for_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Get comprehensive consistency summary for a PDF.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with consistency summary
        """
        associations = self.association_manager.get_associations(pdf_path)
        if not associations:
            return {'error': 'No associations found for PDF'}
        
        # Get association summary
        assoc_summary = self.association_manager.get_association_summary(pdf_path)
        
        # Get consistency percentages
        consistency_percentages = self.get_dynamic_consistency_percentages(pdf_path)
        
        # Get block-level details
        pdf_blocks = [
            state for state in self.block_states.values() 
            if state.pdf_path == pdf_path
        ]
        
        block_details = []
        for state in pdf_blocks:
            consistency = state.current_consistency
            block_details.append({
                'block_id': state.block_id,
                'character_consistency': consistency.character_consistency_score,
                'word_consistency': consistency.word_consistency_score,
                'spelling_accuracy': consistency.spelling_accuracy_score,
                'total_variations': consistency.total_variations,
                'override_terms_count': len(consistency.override_terms),
                'version': state.version
            })
        
        return {
            'pdf_path': pdf_path,
            'association_summary': assoc_summary,
            'consistency_percentages': consistency_percentages,
            'total_tracked_blocks': len(pdf_blocks),
            'block_details': block_details,
            'override_terms_active': len(self.override_manager.get_all_override_terms())
        }
    
    def validate_consistency_state(self, pdf_path: str) -> Dict[str, Any]:
        """
        Validate consistency state for a PDF and identify issues.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        # Check if associations exist
        associations = self.association_manager.get_associations(pdf_path)
        if not associations:
            issues.append("No associations loaded for PDF")
            return {'valid': False, 'issues': issues, 'warnings': warnings}
        
        # Check for failed associations
        failed_associations = [
            meta for meta in associations.metadata.values() 
            if not meta.parsing_success
        ]
        
        if failed_associations:
            warnings.append(f"{len(failed_associations)} associated files failed to parse")
        
        # Check block states
        pdf_blocks = [
            state for state in self.block_states.values() 
            if state.pdf_path == pdf_path
        ]
        
        if not pdf_blocks:
            warnings.append("No blocks tracked for consistency")
        
        # Check for outdated states
        current_files = set(associations.associations.keys())
        for state in pdf_blocks:
            state_files = set(state.associated_files)
            if state_files != current_files:
                warnings.append(f"Block {state.block_id} has outdated file associations")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_associations': len(associations.associations),
            'successful_associations': len([m for m in associations.metadata.values() if m.parsing_success]),
            'tracked_blocks': len(pdf_blocks)
        }


def create_consistency_integration_manager() -> ConsistencyIntegrationManager:
    """Create a new consistency integration manager with default settings."""
    return ConsistencyIntegrationManager()


def track_pdf_consistency(pdf_path: str, block_variations: Dict[str, List[str]]) -> Dict[str, CharacterConsistency]:
    """
    Convenience function to track consistency for all blocks in a PDF.
    
    Args:
        pdf_path: Path to the PDF file
        block_variations: Dictionary mapping block_id to list of variations
        
    Returns:
        Dictionary mapping block_id to CharacterConsistency
    """
    manager = create_consistency_integration_manager()
    
    results = {}
    for block_id, variations in block_variations.items():
        consistency = manager.track_block_consistency_with_associations(
            pdf_path, block_id, variations
        )
        results[block_id] = consistency
    
    return results