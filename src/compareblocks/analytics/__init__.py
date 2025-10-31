# src/compareblocks/analytics/__init__.py
"""
Analytics and reporting system for BECR.
Provides per-engine performance statistics, accuracy metrics, and summary reports.
"""

from .engine_analytics import EngineAnalytics, EnginePerformanceMetrics
from .report_generator import ReportGenerator, AnalyticsReport
from .dashboard import AnalyticsDashboard
from .export import AnalyticsExporter

__all__ = [
    'EngineAnalytics',
    'EnginePerformanceMetrics', 
    'ReportGenerator',
    'AnalyticsReport',
    'AnalyticsDashboard',
    'AnalyticsExporter'
]