# demo_change_tracking.py
"""
Demonstration of the change tracking and source attribution system.
Shows how to track changes, rank sources, and detect propagation.
"""

from compareblocks.tracking import (
    ChangeTracker,
    SourceAttribution,
    SourceRanker,
    ChangePropagationDetector,
    build_neighbor_map,
    rank_sources_by_accuracy,
    get_best_source
)


def demo_basic_tracking():
    """Demonstrate basic change tracking."""
    print("=" * 80)
    print("DEMO 1: Basic Change Tracking")
    print("=" * 80)
    
    tracker = ChangeTracker()
    
    # Create sources
    tesseract = SourceAttribution(
        engine_name="tesseract",
        configuration_hash="config_v1",
        configuration_params={"dpi": 300, "psm": 6},
        confidence_score=0.85
    )
    
    pymupdf = SourceAttribution(
        engine_name="pymupdf",
        configuration_hash="config_default",
        confidence_score=0.92
    )
    
    # Record initial extract
    print("\n1. Recording initial extract...")
    tracker.record_initial_extract("block_001", "The quick brown fox", tesseract)
    print(f"   Initial text: '{tracker.get_current_text('block_001')}'")
    
    # Record consensus selection
    print("\n2. Recording consensus selection...")
    tracker.record_consensus_selection(
        "block_001", "The quick brown fox", pymupdf, 0.95
    )
    print(f"   Current text: '{tracker.get_current_text('block_001')}'")
    
    # Record manual override
    print("\n3. Recording manual override...")
    user = SourceAttribution(engine_name="user", confidence_score=1.0)
    tracker.record_manual_override(
        "block_001", "The quick brown fox.", user, "user123", "Added period"
    )
    print(f"   Final text: '{tracker.get_current_text('block_001')}'")
    
    # Show history
    print("\n4. Change history:")
    history = tracker.get_history("block_001")
    print(f"   Total changes: {len(history.changes)}")
    print(f"   Manual overrides: {history.manual_override_count}")
    print(f"   Current source: {history.get_current_source().engine_name}")
    
    return tracker


def demo_source_ranking(tracker):
    """Demonstrate source ranking."""
    print("\n" + "=" * 80)
    print("DEMO 2: Source Ranking")
    print("=" * 80)
    
    # Add more data for ranking
    sources = {
        "tesseract": SourceAttribution(engine_name="tesseract", confidence_score=0.85),
        "pymupdf": SourceAttribution(engine_name="pymupdf", confidence_score=0.92),
        "paddleocr": SourceAttribution(engine_name="paddleocr", confidence_score=0.88)
    }
    
    # Create more blocks
    for i in range(2, 11):
        block_id = f"block_{i:03d}"
        # Vary which engine is used
        engine_name = ["tesseract", "pymupdf", "paddleocr"][i % 3]
        source = sources[engine_name]
        
        tracker.record_initial_extract(block_id, f"Text {i}", source)
        tracker.record_consensus_selection(
            block_id, f"Final {i}", source, 0.85 + (i % 3) * 0.05
        )
    
    # Rank sources
    print("\n1. Ranking all sources...")
    ranking = rank_sources_by_accuracy(tracker.histories)
    
    print(f"\n   Total sources: {len(ranking.rankings)}")
    print(f"   Total blocks: {ranking.total_blocks}")
    print("\n   Rankings:")
    for i, (source_id, metrics) in enumerate(ranking.rankings, 1):
        print(f"   {i}. {source_id}")
        print(f"      Accuracy Score: {metrics.accuracy_score:.3f}")
        print(f"      Selection Rate: {metrics.selection_rate:.1f}%")
        print(f"      Final Output: {metrics.final_output_contribution} blocks")
    
    # Get best source
    print("\n2. Best performing source:")
    best = get_best_source(tracker.histories)
    print(f"   {best}")
    
    # Compare two sources
    print("\n3. Comparing tesseract vs pymupdf:")
    ranker = SourceRanker()
    comparison = ranker.compare_sources("tesseract", "pymupdf", tracker.histories)
    print(f"   Winner: {comparison['winner']}")
    print(f"   Accuracy difference: {comparison['accuracy_score_diff']:.3f}")
    
    return tracker


def demo_propagation_detection(tracker):
    """Demonstrate propagation detection."""
    print("\n" + "=" * 80)
    print("DEMO 3: Change Propagation Detection")
    print("=" * 80)
    
    source = SourceAttribution(engine_name="tesseract")
    
    # Create a chain of blocks
    print("\n1. Creating block chain...")
    for i in range(20, 25):
        block_id = f"block_{i:03d}"
        tracker.record_initial_extract(block_id, f"Text {i}", source)
    
    # Build neighbor map (linear chain)
    print("\n2. Building neighbor map...")
    positions = {
        f"block_{i:03d}": (1, i * 100, 50)
        for i in range(20, 25)
    }
    neighbor_map = build_neighbor_map(positions)
    
    print("   Neighbors:")
    for block_id, neighbors in neighbor_map.items():
        if neighbors:
            print(f"   {block_id}: {neighbors}")
    
    # Trigger change
    print("\n3. Triggering change in block_020...")
    trigger_change = tracker.record_consensus_selection(
        "block_020", "Updated text 20", source, 0.95
    )
    
    # Simulate propagation
    print("\n4. Simulating propagation...")
    tracker.record_recalculation(
        "block_021", "Recalc text 21", source, ["block_022"], "block_020"
    )
    tracker.record_recalculation(
        "block_022", "Recalc text 22", source, ["block_023"], "block_020"
    )
    
    # Detect propagation
    print("\n5. Detecting propagation chain...")
    detector = ChangePropagationDetector()
    chain = detector.detect_propagation(
        "block_020", trigger_change, tracker.histories, neighbor_map
    )
    
    print(f"   Trigger block: {chain.trigger_block_id}")
    print(f"   Affected blocks: {chain.total_affected_blocks}")
    print(f"   Max depth: {chain.max_propagation_depth}")
    print(f"   Stopped naturally: {chain.stopped_naturally}")
    
    if chain.propagation_steps:
        print("\n   Propagation steps:")
        for step in chain.propagation_steps:
            print(f"   - {step.affected_block_id} (depth {step.propagation_depth})")
    
    return tracker


def demo_statistics():
    """Demonstrate statistics gathering."""
    print("\n" + "=" * 80)
    print("DEMO 4: Statistics and Analytics")
    print("=" * 80)
    
    tracker = ChangeTracker()
    
    # Create diverse data
    engines = ["tesseract", "pymupdf", "paddleocr", "docling"]
    for i in range(50):
        block_id = f"block_{i:03d}"
        engine = engines[i % len(engines)]
        source = SourceAttribution(engine_name=engine, confidence_score=0.8 + (i % 20) * 0.01)
        
        tracker.record_initial_extract(block_id, f"Text {i}", source)
        tracker.record_consensus_selection(block_id, f"Final {i}", source, 0.85 + (i % 15) * 0.01)
        
        # Add some manual overrides
        if i % 10 == 0:
            user = SourceAttribution(engine_name="user")
            tracker.record_manual_override(block_id, f"Manual {i}", user, "user123")
    
    # Get tracker statistics
    print("\n1. Tracker Statistics:")
    stats = tracker.get_statistics()
    print(f"   Total blocks: {stats['total_blocks']}")
    print(f"   Total changes: {stats['total_changes']}")
    print(f"   Blocks with overrides: {stats['blocks_with_manual_overrides']}")
    print(f"   Unique sources: {stats['unique_sources']}")
    
    print("\n   Change type counts:")
    for change_type, count in stats['change_type_counts'].items():
        if count > 0:
            print(f"   - {change_type}: {count}")
    
    # Get ranking statistics
    print("\n2. Source Rankings:")
    ranker = SourceRanker()
    ranking = ranker.rank_sources(tracker.histories)
    summary = ranker.get_ranking_summary(ranking)
    
    print(f"   Best source: {summary['best_source']}")
    print(f"   Best accuracy: {summary['best_accuracy_score']:.3f}")
    print(f"   Worst source: {summary['worst_source']}")
    print(f"   Worst accuracy: {summary['worst_accuracy_score']:.3f}")
    print(f"   Average accuracy: {summary['avg_accuracy_score']:.3f}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "CHANGE TRACKING SYSTEM DEMO" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run demos
    tracker = demo_basic_tracking()
    tracker = demo_source_ranking(tracker)
    tracker = demo_propagation_detection(tracker)
    demo_statistics()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nThe change tracking system provides:")
    print("  ✓ Complete block-level change history")
    print("  ✓ Full source attribution with configuration tracking")
    print("  ✓ Statistical ranking of sources/engines/configurations")
    print("  ✓ Change propagation detection and analysis")
    print("  ✓ NDJSON export/import for persistence")
    print("\nAll features are production-ready and fully tested!")
    print()


if __name__ == "__main__":
    main()
