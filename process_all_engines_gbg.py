#!/usr/bin/env python3
"""
Command-line tool to process all extraction engines with optimized configurations
and integrate results into GBG full analysis.
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from compareblocks.engines.comprehensive_engine_gbg_processor import (
    ComprehensiveEngineGBGProcessor,
    OverwriteMode,
    process_all_engines_with_gbg_integration,
    process_engines_with_gbg_integration,
    get_available_engines_for_gbg_integration
)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Process all extraction engines with optimized configurations and integrate into GBG analysis"
    )
    
    parser.add_argument(
        "--pdf-path",
        type=str,
        help="Path to PDF file (uses default from file manager if not specified)"
    )
    
    parser.add_argument(
        "--gbg-analysis-path",
        type=str,
        help="Path to existing GBG analysis file (auto-detected if not specified)"
    )
    
    parser.add_argument(
        "--engines",
        type=str,
        nargs="+",
        help="Specific engines to process (processes all available if not specified)"
    )
    
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List available engines and exit"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--overwrite-mode",
        type=str,
        choices=["overwrite", "skip", "allow_multiple"],
        default="skip",
        help="How to handle existing results with same engine+config (default: skip)"
    )
    
    parser.add_argument(
        "--compare-configurations",
        action="store_true",
        help="Test multiple configurations for each engine and compare performance"
    )
    
    args = parser.parse_args()
    
    # List available engines
    if args.list_engines:
        engines = get_available_engines_for_gbg_integration()
        print("Available engines:")
        for engine in engines:
            print(f"  - {engine}")
        return
    
    # Process engines
    try:
        # Set up overwrite mode
        overwrite_mode = OverwriteMode(args.overwrite_mode)
        
        # Create processor with specified overwrite mode
        processor = ComprehensiveEngineGBGProcessor(overwrite_mode=overwrite_mode)
        
        if args.compare_configurations:
            print("🔬 Configuration comparison mode enabled")
            # TODO: Implement configuration comparison workflow
            print("Configuration comparison not yet implemented in CLI")
            return
        
        if args.engines:
            print(f"Processing specific engines: {args.engines}")
            result = processor.process_specific_engines(
                engine_names=args.engines,
                pdf_path=args.pdf_path,
                gbg_analysis_path=args.gbg_analysis_path
            )
        else:
            print("Processing all available engines...")
            result = processor.process_all_engines_comprehensive(
                pdf_path=args.pdf_path,
                gbg_analysis_path=args.gbg_analysis_path
            )
        
        # Display results
        if result.success:
            print(f"\n✅ Processing completed successfully!")
            print(f"Updated GBG analysis: {result.updated_gbg_analysis_path}")
            print(f"Engines processed: {result.engines_processed}")
            print(f"Engines optimized: {result.engines_optimized}")
            print(f"Engines failed: {result.engines_failed}")
            print(f"Total processing time: {result.total_processing_time:.1f}s")
            
            if args.verbose:
                print("\nEngine details:")
                for engine_name, engine_result in result.engine_results.items():
                    status = "✅" if engine_result.success else "❌"
                    opt_status = "🔧" if engine_result.is_optimized else "📋"
                    print(f"  {status} {opt_status} {engine_name}: {engine_result.extraction_time:.1f}s")
                    if not engine_result.success:
                        print(f"    Error: {engine_result.error_message}")
                    if engine_result.is_optimized:
                        print(f"    Config source: {engine_result.config_source}")
        else:
            print(f"\n❌ Processing failed!")
            if "error" in result.processing_summary:
                print(f"Error: {result.processing_summary['error']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()