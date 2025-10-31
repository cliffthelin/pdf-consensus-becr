# src/compareblocks/analytics/export.py
"""
Analytics export functionality for downstream analysis.
Exports analytics data in various formats for external tools and analysis.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import asdict

from .engine_analytics import EnginePerformanceMetrics
from .report_generator import AnalyticsReport
from ..io.writer import AnalyticsWriter
from ..config.file_manager import file_manager


class AnalyticsExporter:
    """Exports analytics data in various formats for downstream analysis."""
    
    def __init__(self):
        """Initialize analytics exporter."""
        self.analytics_writer = AnalyticsWriter()
    
    def export_engine_metrics_json(self, metrics: Dict[str, EnginePerformanceMetrics],
                                 output_path: Optional[Path] = None) -> Path:
        """
        Export engine metrics to JSON format.
        
        Args:
            metrics: Dictionary of engine performance metrics
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"engine_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert metrics to serializable format
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'export_type': 'engine_metrics',
            'total_engines': len(metrics),
            'metrics': {
                engine_name: metric.to_dict()
                for engine_name, metric in metrics.items()
            }
        }
        
        # Export to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_engine_metrics_csv(self, metrics: Dict[str, EnginePerformanceMetrics],
                                output_path: Optional[Path] = None) -> Path:
        """
        Export engine metrics to CSV format.
        
        Args:
            metrics: Dictionary of engine performance metrics
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"engine_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Define CSV columns
        columns = [
            'engine_name',
            'total_extractions',
            'successful_extractions',
            'failed_extractions',
            'success_rate',
            'avg_extraction_time',
            'min_extraction_time',
            'max_extraction_time',
            'total_extraction_time',
            'avg_score',
            'min_score',
            'max_score',
            'score_variance',
            'selections_count',
            'selection_rate',
            'manual_override_count',
            'manual_override_rate',
            'anomaly_detection_count',
            'anomaly_detection_rate'
        ]
        
        # Export to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for engine_name, metric in metrics.items():
                row = {
                    'engine_name': engine_name,
                    'total_extractions': metric.total_extractions,
                    'successful_extractions': metric.successful_extractions,
                    'failed_extractions': metric.failed_extractions,
                    'success_rate': metric.success_rate,
                    'avg_extraction_time': metric.avg_extraction_time,
                    'min_extraction_time': metric.min_extraction_time,
                    'max_extraction_time': metric.max_extraction_time,
                    'total_extraction_time': metric.total_extraction_time,
                    'avg_score': metric.avg_score,
                    'min_score': metric.min_score,
                    'max_score': metric.max_score,
                    'score_variance': metric.score_variance,
                    'selections_count': metric.selections_count,
                    'selection_rate': metric.selection_rate,
                    'manual_override_count': metric.manual_override_count,
                    'manual_override_rate': metric.manual_override_rate,
                    'anomaly_detection_count': metric.anomaly_detection_count,
                    'anomaly_detection_rate': metric.anomaly_detection_rate
                }
                writer.writerow(row)
        
        return output_path
    
    def export_engine_metrics_ndjson(self, metrics: Dict[str, EnginePerformanceMetrics],
                                   output_path: Optional[Path] = None) -> Path:
        """
        Export engine metrics to NDJSON format.
        
        Args:
            metrics: Dictionary of engine performance metrics
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"engine_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export each metric as a separate NDJSON line
        with open(output_path, 'w', encoding='utf-8') as f:
            for engine_name, metric in metrics.items():
                record = {
                    'record_type': 'engine_performance_metric',
                    'timestamp': datetime.now().isoformat(),
                    'engine_name': engine_name,
                    **metric.to_dict()
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return output_path
    
    def export_analytics_report(self, report: AnalyticsReport,
                              format_type: str = 'json',
                              output_path: Optional[Path] = None) -> Path:
        """
        Export analytics report in specified format.
        
        Args:
            report: Analytics report to export
            format_type: Export format ('json', 'ndjson', 'csv')
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if format_type.lower() == 'json':
            return self._export_report_json(report, output_path)
        elif format_type.lower() == 'ndjson':
            return self._export_report_ndjson(report, output_path)
        elif format_type.lower() == 'csv':
            return self._export_report_csv(report, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_report_json(self, report: AnalyticsReport, output_path: Optional[Path] = None) -> Path:
        """Export report to JSON format."""
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"analytics_report_{report.report_id}.json"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def _export_report_ndjson(self, report: AnalyticsReport, output_path: Optional[Path] = None) -> Path:
        """Export report to NDJSON format."""
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"analytics_report_{report.report_id}.ndjson"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert report to NDJSON records
        analytics_data = {
            'timestamp': report.timestamp,
            'summary': report.summary,
            'engine_stats': {
                engine: metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics
                for engine, metrics in report.engine_performance.items()
            }
        }
        
        # Use analytics writer for NDJSON export
        self.analytics_writer.write_analytics_report(analytics_data, output_path, overwrite=True)
        
        return output_path
    
    def _export_report_csv(self, report: AnalyticsReport, output_path: Optional[Path] = None) -> Path:
        """Export report summary to CSV format."""
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"analytics_report_summary_{report.report_id}.csv"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create CSV with report summary and engine metrics
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write report header
            writer.writerow(['Report Information'])
            writer.writerow(['Report ID', report.report_id])
            writer.writerow(['Timestamp', report.timestamp])
            writer.writerow(['Report Type', report.report_type])
            writer.writerow(['PDF Path', report.pdf_path])
            writer.writerow(['PDF Name', report.pdf_name])
            writer.writerow([])  # Empty row
            
            # Write summary
            writer.writerow(['Summary'])
            for key, value in report.summary.items():
                if isinstance(value, (str, int, float)):
                    writer.writerow([key, value])
            writer.writerow([])  # Empty row
            
            # Write engine performance metrics
            if report.engine_performance:
                writer.writerow(['Engine Performance Metrics'])
                
                # Header row for metrics
                metrics_headers = [
                    'Engine', 'Total Extractions', 'Success Rate', 'Avg Score',
                    'Selection Rate', 'Manual Override Rate', 'Anomaly Rate'
                ]
                writer.writerow(metrics_headers)
                
                # Data rows
                for engine, metrics in report.engine_performance.items():
                    if hasattr(metrics, 'to_dict'):
                        m = metrics
                        writer.writerow([
                            engine,
                            m.total_extractions,
                            f"{m.success_rate:.1f}%",
                            f"{m.avg_score:.3f}",
                            f"{m.selection_rate:.1f}%",
                            f"{m.manual_override_rate:.1f}%",
                            f"{m.anomaly_detection_rate:.1f}%"
                        ])
        
        return output_path
    
    def export_dashboard_data(self, dashboard_data: Dict[str, Any],
                            output_path: Optional[Path] = None) -> Path:
        """
        Export dashboard data for external visualization tools.
        
        Args:
            dashboard_data: Dashboard data dictionary
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add export metadata
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'export_type': 'dashboard_data',
            'dashboard_title': dashboard_data.get('title', 'Unknown Dashboard'),
            'data': dashboard_data
        }
        
        # Export to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_comparison_data(self, comparison_data: Dict[str, Any],
                             output_path: Optional[Path] = None) -> Path:
        """
        Export comparison data for trend analysis.
        
        Args:
            comparison_data: Comparison data dictionary
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"comparison_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def export_batch_metrics(self, metrics_list: List[Dict[str, EnginePerformanceMetrics]],
                           output_path: Optional[Path] = None) -> Path:
        """
        Export multiple sets of engine metrics for batch analysis.
        
        Args:
            metrics_list: List of engine metrics dictionaries
            output_path: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_dir = Path(file_manager.get_processing_directory())
            filename = f"batch_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ndjson"
            output_path = output_dir / filename
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Export each metrics set as NDJSON records
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, metrics in enumerate(metrics_list):
                batch_record = {
                    'record_type': 'batch_metrics',
                    'batch_index': i,
                    'timestamp': datetime.now().isoformat(),
                    'total_engines': len(metrics),
                    'metrics': {
                        engine: metric.to_dict()
                        for engine, metric in metrics.items()
                    }
                }
                f.write(json.dumps(batch_record, ensure_ascii=False) + '\n')
        
        return output_path
    
    def create_export_summary(self, exported_files: List[Path]) -> Dict[str, Any]:
        """
        Create a summary of exported files.
        
        Args:
            exported_files: List of exported file paths
            
        Returns:
            Export summary dictionary
        """
        summary = {
            'export_timestamp': datetime.now().isoformat(),
            'total_files': len(exported_files),
            'files': []
        }
        
        for file_path in exported_files:
            file_info = {
                'path': str(file_path),
                'filename': file_path.name,
                'size_bytes': file_path.stat().st_size if file_path.exists() else 0,
                'format': file_path.suffix.lower(),
                'created': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat() if file_path.exists() else None
            }
            summary['files'].append(file_info)
        
        return summary


def export_engine_metrics(metrics: Dict[str, EnginePerformanceMetrics],
                         format_type: str = 'json',
                         output_path: Optional[Path] = None) -> Path:
    """
    Convenience function to export engine metrics.
    
    Args:
        metrics: Dictionary of engine performance metrics
        format_type: Export format ('json', 'csv', 'ndjson')
        output_path: Optional output file path
        
    Returns:
        Path to exported file
    """
    exporter = AnalyticsExporter()
    
    if format_type.lower() == 'json':
        return exporter.export_engine_metrics_json(metrics, output_path)
    elif format_type.lower() == 'csv':
        return exporter.export_engine_metrics_csv(metrics, output_path)
    elif format_type.lower() == 'ndjson':
        return exporter.export_engine_metrics_ndjson(metrics, output_path)
    else:
        raise ValueError(f"Unsupported export format: {format_type}")


def export_analytics_report(report: AnalyticsReport,
                          format_type: str = 'json',
                          output_path: Optional[Path] = None) -> Path:
    """
    Convenience function to export analytics report.
    
    Args:
        report: Analytics report to export
        format_type: Export format ('json', 'ndjson', 'csv')
        output_path: Optional output file path
        
    Returns:
        Path to exported file
    """
    exporter = AnalyticsExporter()
    return exporter.export_analytics_report(report, format_type, output_path)