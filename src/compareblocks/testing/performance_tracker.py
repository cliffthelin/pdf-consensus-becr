# src/compareblocks/testing/performance_tracker.py
"""
Performance Metrics Tracking System

Tracks performance metrics for engine functions across different PDF files.
Maintains historical performance data and identifies optimization opportunities.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import time
import statistics
from datetime import datetime, timedelta

from ..config.file_manager import file_manager


@dataclass
class PerformanceMetric:
    """Performance metric for a single test run."""
    engine_name: str
    function_name: str
    pdf_file: str
    pdf_size_mb: float
    pdf_pages: int
    execution_time: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    output_size_bytes: int = 0
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class PerformanceBenchmark:
    """Performance benchmark for an engine function."""
    engine_name: str
    function_name: str
    avg_execution_time: float
    min_execution_time: float
    max_execution_time: float
    std_execution_time: float
    avg_throughput_pages_per_sec: float
    avg_memory_usage_mb: float
    success_rate: float
    total_tests: int
    benchmark_timestamp: str


@dataclass
class OptimizationOpportunity:
    """Represents a performance optimization opportunity."""
    engine_name: str
    function_name: str
    issue_type: str  # 'slow_execution', 'high_memory', 'low_success_rate', 'inconsistent_performance'
    severity: str  # 'low', 'medium', 'high', 'critical'
    description: str
    current_metric: float
    target_metric: float
    improvement_potential: float
    recommendation: str


class PerformanceTracker:
    """Tracks and analyzes performance metrics for engine functions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize performance tracker.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path("output/engine_testing/performance_tracking.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for performance tracking."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine_name TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    pdf_file TEXT NOT NULL,
                    pdf_size_mb REAL NOT NULL,
                    pdf_pages INTEGER NOT NULL,
                    execution_time REAL NOT NULL,
                    memory_usage_mb REAL,
                    cpu_usage_percent REAL,
                    output_size_bytes INTEGER DEFAULT 0,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            # Performance benchmarks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine_name TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    avg_execution_time REAL NOT NULL,
                    min_execution_time REAL NOT NULL,
                    max_execution_time REAL NOT NULL,
                    std_execution_time REAL NOT NULL,
                    avg_throughput_pages_per_sec REAL NOT NULL,
                    avg_memory_usage_mb REAL NOT NULL,
                    success_rate REAL NOT NULL,
                    total_tests INTEGER NOT NULL,
                    benchmark_timestamp TEXT NOT NULL,
                    UNIQUE(engine_name, function_name, benchmark_timestamp)
                )
            ''')
            
            # Optimization opportunities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine_name TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    issue_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    current_metric REAL NOT NULL,
                    target_metric REAL NOT NULL,
                    improvement_potential REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    identified_timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def record_performance_metric(self, metric: PerformanceMetric):
        """
        Record a performance metric.
        
        Args:
            metric: Performance metric to record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (engine_name, function_name, pdf_file, pdf_size_mb, pdf_pages,
                 execution_time, memory_usage_mb, cpu_usage_percent, 
                 output_size_bytes, success, error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric.engine_name,
                metric.function_name,
                metric.pdf_file,
                metric.pdf_size_mb,
                metric.pdf_pages,
                metric.execution_time,
                metric.memory_usage_mb,
                metric.cpu_usage_percent,
                metric.output_size_bytes,
                metric.success,
                metric.error_message,
                metric.timestamp
            ))
            
            conn.commit()
    
    def calculate_benchmarks(self, engine_name: str, function_name: str,
                           days_back: int = 30) -> Optional[PerformanceBenchmark]:
        """
        Calculate performance benchmarks for an engine function.
        
        Args:
            engine_name: Name of the engine
            function_name: Name of the function
            days_back: Number of days to look back for data
            
        Returns:
            Performance benchmark or None if insufficient data
        """
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d %H:%M:%S")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT execution_time, memory_usage_mb, pdf_pages, success
                FROM performance_metrics 
                WHERE engine_name = ? AND function_name = ? 
                AND timestamp >= ? AND success = 1
                ORDER BY timestamp DESC
            ''', (engine_name, function_name, cutoff_date))
            
            rows = cursor.fetchall()
            
            if len(rows) < 3:  # Need at least 3 data points
                return None
            
            execution_times = [row[0] for row in rows]
            memory_usages = [row[1] for row in rows if row[1] is not None]
            page_counts = [row[2] for row in rows]
            
            # Calculate throughput (pages per second)
            throughputs = []
            for i, row in enumerate(rows):
                if execution_times[i] > 0 and page_counts[i] > 0:
                    throughputs.append(page_counts[i] / execution_times[i])
            
            # Calculate success rate
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
                FROM performance_metrics 
                WHERE engine_name = ? AND function_name = ? AND timestamp >= ?
            ''', (engine_name, function_name, cutoff_date))
            
            total, successful = cursor.fetchone()
            success_rate = (successful / total * 100) if total > 0 else 0
            
            benchmark = PerformanceBenchmark(
                engine_name=engine_name,
                function_name=function_name,
                avg_execution_time=statistics.mean(execution_times),
                min_execution_time=min(execution_times),
                max_execution_time=max(execution_times),
                std_execution_time=statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
                avg_throughput_pages_per_sec=statistics.mean(throughputs) if throughputs else 0,
                avg_memory_usage_mb=statistics.mean(memory_usages) if memory_usages else 0,
                success_rate=success_rate,
                total_tests=len(rows),
                benchmark_timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            # Save benchmark
            cursor.execute('''
                INSERT OR REPLACE INTO performance_benchmarks 
                (engine_name, function_name, avg_execution_time, min_execution_time,
                 max_execution_time, std_execution_time, avg_throughput_pages_per_sec,
                 avg_memory_usage_mb, success_rate, total_tests, benchmark_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                benchmark.engine_name,
                benchmark.function_name,
                benchmark.avg_execution_time,
                benchmark.min_execution_time,
                benchmark.max_execution_time,
                benchmark.std_execution_time,
                benchmark.avg_throughput_pages_per_sec,
                benchmark.avg_memory_usage_mb,
                benchmark.success_rate,
                benchmark.total_tests,
                benchmark.benchmark_timestamp
            ))
            
            conn.commit()
            
            return benchmark
    
    def identify_optimization_opportunities(self, engine_name: Optional[str] = None) -> List[OptimizationOpportunity]:
        """
        Identify performance optimization opportunities.
        
        Args:
            engine_name: Specific engine name, or None for all engines
            
        Returns:
            List of optimization opportunities
        """
        opportunities = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get recent benchmarks
            if engine_name:
                cursor.execute('''
                    SELECT engine_name, function_name, avg_execution_time, 
                           avg_throughput_pages_per_sec, avg_memory_usage_mb, success_rate
                    FROM performance_benchmarks 
                    WHERE engine_name = ?
                    ORDER BY benchmark_timestamp DESC
                ''', (engine_name,))
            else:
                cursor.execute('''
                    SELECT engine_name, function_name, avg_execution_time, 
                           avg_throughput_pages_per_sec, avg_memory_usage_mb, success_rate
                    FROM performance_benchmarks 
                    ORDER BY benchmark_timestamp DESC
                ''')
            
            benchmarks = cursor.fetchall()
            
            for benchmark in benchmarks:
                eng_name, func_name, avg_time, throughput, memory, success_rate = benchmark
                
                # Check for slow execution (> 10 seconds average)
                if avg_time > 10.0:
                    opportunities.append(OptimizationOpportunity(
                        engine_name=eng_name,
                        function_name=func_name,
                        issue_type="slow_execution",
                        severity="high" if avg_time > 30.0 else "medium",
                        description=f"Average execution time is {avg_time:.1f} seconds",
                        current_metric=avg_time,
                        target_metric=5.0,
                        improvement_potential=((avg_time - 5.0) / avg_time * 100),
                        recommendation="Optimize algorithm or consider parallel processing"
                    ))
                
                # Check for high memory usage (> 500 MB average)
                if memory > 500.0:
                    opportunities.append(OptimizationOpportunity(
                        engine_name=eng_name,
                        function_name=func_name,
                        issue_type="high_memory",
                        severity="high" if memory > 1000.0 else "medium",
                        description=f"Average memory usage is {memory:.1f} MB",
                        current_metric=memory,
                        target_metric=200.0,
                        improvement_potential=((memory - 200.0) / memory * 100),
                        recommendation="Implement memory-efficient processing or streaming"
                    ))
                
                # Check for low success rate (< 90%)
                if success_rate < 90.0:
                    opportunities.append(OptimizationOpportunity(
                        engine_name=eng_name,
                        function_name=func_name,
                        issue_type="low_success_rate",
                        severity="critical" if success_rate < 70.0 else "high",
                        description=f"Success rate is only {success_rate:.1f}%",
                        current_metric=success_rate,
                        target_metric=95.0,
                        improvement_potential=(95.0 - success_rate),
                        recommendation="Improve error handling and input validation"
                    ))
                
                # Check for low throughput (< 1 page per second)
                if throughput > 0 and throughput < 1.0:
                    opportunities.append(OptimizationOpportunity(
                        engine_name=eng_name,
                        function_name=func_name,
                        issue_type="low_throughput",
                        severity="medium",
                        description=f"Throughput is only {throughput:.2f} pages/second",
                        current_metric=throughput,
                        target_metric=2.0,
                        improvement_potential=((2.0 - throughput) / 2.0 * 100),
                        recommendation="Optimize processing pipeline for better throughput"
                    ))
            
            # Check for inconsistent performance
            cursor.execute('''
                SELECT engine_name, function_name, std_execution_time, avg_execution_time
                FROM performance_benchmarks 
                WHERE std_execution_time > avg_execution_time * 0.5
            ''')
            
            inconsistent = cursor.fetchall()
            
            for row in inconsistent:
                eng_name, func_name, std_time, avg_time = row
                
                opportunities.append(OptimizationOpportunity(
                    engine_name=eng_name,
                    function_name=func_name,
                    issue_type="inconsistent_performance",
                    severity="medium",
                    description=f"High performance variance (std: {std_time:.1f}s, avg: {avg_time:.1f}s)",
                    current_metric=std_time / avg_time,
                    target_metric=0.2,
                    improvement_potential=50.0,
                    recommendation="Investigate and reduce performance variability"
                ))
        
        return opportunities
    
    def get_performance_comparison(self, engine_names: List[str], 
                                 function_name: str) -> Dict[str, Any]:
        """
        Compare performance across multiple engines for a function.
        
        Args:
            engine_names: List of engine names to compare
            function_name: Function name to compare
            
        Returns:
            Performance comparison data
        """
        comparison = {
            "function_name": function_name,
            "engines": {},
            "rankings": {},
            "comparison_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        benchmarks = []
        
        for engine_name in engine_names:
            benchmark = self.calculate_benchmarks(engine_name, function_name)
            
            if benchmark:
                comparison["engines"][engine_name] = asdict(benchmark)
                benchmarks.append((engine_name, benchmark))
        
        if benchmarks:
            # Rank by execution time (lower is better)
            time_ranking = sorted(benchmarks, key=lambda x: x[1].avg_execution_time)
            comparison["rankings"]["execution_time"] = [eng for eng, _ in time_ranking]
            
            # Rank by throughput (higher is better)
            throughput_ranking = sorted(benchmarks, key=lambda x: x[1].avg_throughput_pages_per_sec, reverse=True)
            comparison["rankings"]["throughput"] = [eng for eng, _ in throughput_ranking]
            
            # Rank by success rate (higher is better)
            success_ranking = sorted(benchmarks, key=lambda x: x[1].success_rate, reverse=True)
            comparison["rankings"]["success_rate"] = [eng for eng, _ in success_ranking]
            
            # Rank by memory usage (lower is better)
            memory_ranking = sorted(benchmarks, key=lambda x: x[1].avg_memory_usage_mb)
            comparison["rankings"]["memory_usage"] = [eng for eng, _ in memory_ranking]
        
        return comparison
    
    def generate_performance_report(self, engine_name: Optional[str] = None,
                                  days_back: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Args:
            engine_name: Specific engine name, or None for all engines
            days_back: Number of days to include in analysis
            
        Returns:
            Performance report data
        """
        report = {
            "report_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "analysis_period_days": days_back,
            "scope": engine_name or "all_engines",
            "benchmarks": {},
            "optimization_opportunities": [],
            "performance_trends": {},
            "summary": {}
        }
        
        # Get benchmarks
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if engine_name:
                cursor.execute('''
                    SELECT DISTINCT engine_name, function_name 
                    FROM performance_metrics 
                    WHERE engine_name = ?
                ''', (engine_name,))
            else:
                cursor.execute('''
                    SELECT DISTINCT engine_name, function_name 
                    FROM performance_metrics
                ''')
            
            engine_functions = cursor.fetchall()
            
            for eng_name, func_name in engine_functions:
                benchmark = self.calculate_benchmarks(eng_name, func_name, days_back)
                
                if benchmark:
                    if eng_name not in report["benchmarks"]:
                        report["benchmarks"][eng_name] = {}
                    
                    report["benchmarks"][eng_name][func_name] = asdict(benchmark)
        
        # Get optimization opportunities
        opportunities = self.identify_optimization_opportunities(engine_name)
        report["optimization_opportunities"] = [asdict(opp) for opp in opportunities]
        
        # Calculate summary statistics
        all_benchmarks = []
        for engine_benchmarks in report["benchmarks"].values():
            for benchmark in engine_benchmarks.values():
                all_benchmarks.append(benchmark)
        
        if all_benchmarks:
            avg_execution_time = statistics.mean([b["avg_execution_time"] for b in all_benchmarks])
            avg_success_rate = statistics.mean([b["success_rate"] for b in all_benchmarks])
            avg_throughput = statistics.mean([b["avg_throughput_pages_per_sec"] for b in all_benchmarks if b["avg_throughput_pages_per_sec"] > 0])
            
            report["summary"] = {
                "total_engine_functions": len(all_benchmarks),
                "avg_execution_time": avg_execution_time,
                "avg_success_rate": avg_success_rate,
                "avg_throughput_pages_per_sec": avg_throughput,
                "total_optimization_opportunities": len(opportunities),
                "critical_issues": len([opp for opp in opportunities if opp.severity == "critical"]),
                "high_priority_issues": len([opp for opp in opportunities if opp.severity == "high"])
            }
        
        return report
    
    def export_performance_data(self, output_path: Optional[str] = None) -> str:
        """
        Export performance data to JSON file.
        
        Args:
            output_path: Path to save export file
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = Path("output/engine_testing/performance_export.json")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive report
        report = self.generate_performance_report()
        
        # Add raw metrics data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM performance_metrics 
                ORDER BY timestamp DESC LIMIT 1000
            ''')
            
            raw_metrics = [dict(zip([col[0] for col in cursor.description], row)) 
                          for row in cursor.fetchall()]
            
            report["raw_metrics"] = raw_metrics
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Performance data exported to: {output_path}")
        return str(output_path)


# Convenience functions
def record_performance(engine_name: str, function_name: str, pdf_file: str,
                      pdf_size_mb: float, pdf_pages: int, execution_time: float,
                      success: bool = True, memory_usage_mb: Optional[float] = None,
                      cpu_usage_percent: Optional[float] = None,
                      output_size_bytes: int = 0, error_message: Optional[str] = None):
    """Record a performance metric."""
    tracker = PerformanceTracker()
    
    metric = PerformanceMetric(
        engine_name=engine_name,
        function_name=function_name,
        pdf_file=pdf_file,
        pdf_size_mb=pdf_size_mb,
        pdf_pages=pdf_pages,
        execution_time=execution_time,
        memory_usage_mb=memory_usage_mb,
        cpu_usage_percent=cpu_usage_percent,
        output_size_bytes=output_size_bytes,
        success=success,
        error_message=error_message
    )
    
    tracker.record_performance_metric(metric)


def generate_performance_report(engine_name: Optional[str] = None) -> Dict[str, Any]:
    """Generate performance report for engines."""
    tracker = PerformanceTracker()
    return tracker.generate_performance_report(engine_name)


def compare_engine_performance(engine_names: List[str], function_name: str) -> Dict[str, Any]:
    """Compare performance across engines for a function."""
    tracker = PerformanceTracker()
    return tracker.get_performance_comparison(engine_names, function_name)