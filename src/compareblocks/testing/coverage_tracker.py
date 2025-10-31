# src/compareblocks/testing/coverage_tracker.py
"""
Test Coverage Tracking System

Tracks test coverage for engine functions and parameters.
Maintains historical data and identifies gaps in testing.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import time
from datetime import datetime, timedelta

from ..config.file_manager import file_manager


@dataclass
class ParameterTestRecord:
    """Record of parameter testing for a function."""
    function_name: str
    engine_name: str
    parameter_set: Dict[str, Any]
    test_timestamp: str
    test_success: bool
    execution_time: float
    pdf_file: str
    test_output_size: int
    error_message: Optional[str] = None


@dataclass
class FileTypeTestRecord:
    """Record of file type testing for an engine."""
    engine_name: str
    file_type: str
    file_path: str
    test_timestamp: str
    test_success: bool
    extraction_time: float
    output_quality_score: Optional[float] = None
    error_message: Optional[str] = None


@dataclass
class CoverageGap:
    """Represents a gap in test coverage."""
    gap_type: str  # 'function', 'parameter', 'file_type'
    engine_name: str
    function_name: Optional[str] = None
    missing_parameters: Optional[List[str]] = None
    missing_file_types: Optional[List[str]] = None
    priority: str = "medium"  # 'low', 'medium', 'high', 'critical'
    recommendation: Optional[str] = None


class CoverageTracker:
    """Tracks and manages test coverage for engine functions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize coverage tracker.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path("output/engine_testing/coverage_tracking.db")
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for coverage tracking."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            
            # Parameter test records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS parameter_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    function_name TEXT NOT NULL,
                    engine_name TEXT NOT NULL,
                    parameter_set TEXT NOT NULL,  -- JSON string
                    test_timestamp TEXT NOT NULL,
                    test_success BOOLEAN NOT NULL,
                    execution_time REAL NOT NULL,
                    pdf_file TEXT NOT NULL,
                    test_output_size INTEGER NOT NULL,
                    error_message TEXT,
                    UNIQUE(function_name, engine_name, parameter_set, pdf_file)
                )
            ''')
            
            # File type test records table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_type_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    test_timestamp TEXT NOT NULL,
                    test_success BOOLEAN NOT NULL,
                    extraction_time REAL NOT NULL,
                    output_quality_score REAL,
                    error_message TEXT,
                    UNIQUE(engine_name, file_type, file_path)
                )
            ''')
            
            # Coverage summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS coverage_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    engine_name TEXT NOT NULL,
                    function_name TEXT NOT NULL,
                    total_parameters_tested INTEGER DEFAULT 0,
                    total_file_types_tested INTEGER DEFAULT 0,
                    last_test_timestamp TEXT,
                    coverage_score REAL DEFAULT 0.0,
                    UNIQUE(engine_name, function_name)
                )
            ''')
            
            conn.commit()
        finally:
            conn.close()
    
    def record_parameter_test(self, record: ParameterTestRecord):
        """
        Record a parameter test result.
        
        Args:
            record: Parameter test record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert or update parameter test record
            cursor.execute('''
                INSERT OR REPLACE INTO parameter_tests 
                (function_name, engine_name, parameter_set, test_timestamp, 
                 test_success, execution_time, pdf_file, test_output_size, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.function_name,
                record.engine_name,
                json.dumps(record.parameter_set, sort_keys=True),
                record.test_timestamp,
                record.test_success,
                record.execution_time,
                record.pdf_file,
                record.test_output_size,
                record.error_message
            ))
            
            # Update coverage summary
            self._update_coverage_summary(cursor, record.engine_name, record.function_name)
            
            conn.commit()
    
    def record_file_type_test(self, record: FileTypeTestRecord):
        """
        Record a file type test result.
        
        Args:
            record: File type test record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert or update file type test record
            cursor.execute('''
                INSERT OR REPLACE INTO file_type_tests 
                (engine_name, file_type, file_path, test_timestamp, 
                 test_success, extraction_time, output_quality_score, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.engine_name,
                record.file_type,
                record.file_path,
                record.test_timestamp,
                record.test_success,
                record.extraction_time,
                record.output_quality_score,
                record.error_message
            ))
            
            conn.commit()
    
    def _update_coverage_summary(self, cursor, engine_name: str, function_name: str):
        """Update coverage summary for a function."""
        # Count parameter tests
        cursor.execute('''
            SELECT COUNT(DISTINCT parameter_set) 
            FROM parameter_tests 
            WHERE engine_name = ? AND function_name = ?
        ''', (engine_name, function_name))
        
        param_count = cursor.fetchone()[0]
        
        # Count file type tests (for the engine overall)
        cursor.execute('''
            SELECT COUNT(DISTINCT file_type) 
            FROM file_type_tests 
            WHERE engine_name = ?
        ''', (engine_name,))
        
        file_type_count = cursor.fetchone()[0]
        
        # Get latest test timestamp
        cursor.execute('''
            SELECT MAX(test_timestamp) 
            FROM parameter_tests 
            WHERE engine_name = ? AND function_name = ?
        ''', (engine_name, function_name))
        
        latest_timestamp = cursor.fetchone()[0]
        
        # Calculate coverage score (simple metric based on parameter and file type diversity)
        coverage_score = min(100.0, (param_count * 10) + (file_type_count * 5))
        
        # Insert or update coverage summary
        cursor.execute('''
            INSERT OR REPLACE INTO coverage_summary 
            (engine_name, function_name, total_parameters_tested, 
             total_file_types_tested, last_test_timestamp, coverage_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            engine_name,
            function_name,
            param_count,
            file_type_count,
            latest_timestamp,
            coverage_score
        ))
    
    def get_parameter_coverage(self, engine_name: str, function_name: str) -> Dict[str, Any]:
        """
        Get parameter coverage for a specific function.
        
        Args:
            engine_name: Name of the engine
            function_name: Name of the function
            
        Returns:
            Parameter coverage information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all parameter tests for this function
            cursor.execute('''
                SELECT parameter_set, test_timestamp, test_success, execution_time, 
                       pdf_file, test_output_size, error_message
                FROM parameter_tests 
                WHERE engine_name = ? AND function_name = ?
                ORDER BY test_timestamp DESC
            ''', (engine_name, function_name))
            
            rows = cursor.fetchall()
            
            parameter_tests = []
            unique_parameters = set()
            
            for row in rows:
                param_set = json.loads(row[0])
                unique_parameters.add(json.dumps(param_set, sort_keys=True))
                
                parameter_tests.append({
                    "parameter_set": param_set,
                    "test_timestamp": row[1],
                    "test_success": row[2],
                    "execution_time": row[3],
                    "pdf_file": row[4],
                    "test_output_size": row[5],
                    "error_message": row[6]
                })
            
            return {
                "engine_name": engine_name,
                "function_name": function_name,
                "total_parameter_combinations": len(unique_parameters),
                "total_tests": len(parameter_tests),
                "parameter_tests": parameter_tests,
                "unique_parameter_sets": [json.loads(p) for p in unique_parameters]
            }
    
    def get_file_type_coverage(self, engine_name: str) -> Dict[str, Any]:
        """
        Get file type coverage for an engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            File type coverage information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all file type tests for this engine
            cursor.execute('''
                SELECT file_type, file_path, test_timestamp, test_success, 
                       extraction_time, output_quality_score, error_message
                FROM file_type_tests 
                WHERE engine_name = ?
                ORDER BY test_timestamp DESC
            ''', (engine_name,))
            
            rows = cursor.fetchall()
            
            file_type_tests = []
            tested_file_types = set()
            
            for row in rows:
                tested_file_types.add(row[0])
                
                file_type_tests.append({
                    "file_type": row[0],
                    "file_path": row[1],
                    "test_timestamp": row[2],
                    "test_success": row[3],
                    "extraction_time": row[4],
                    "output_quality_score": row[5],
                    "error_message": row[6]
                })
            
            return {
                "engine_name": engine_name,
                "tested_file_types": list(tested_file_types),
                "total_file_type_tests": len(file_type_tests),
                "file_type_tests": file_type_tests
            }
    
    def identify_coverage_gaps(self, engine_name: str) -> List[CoverageGap]:
        """
        Identify coverage gaps for an engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            List of coverage gaps
        """
        gaps = []
        
        # Define expected parameters for common functions
        expected_parameters = {
            "extract_pdf": [
                {"pdf_path": None},  # Default path
                {"pdf_path": "custom_path.pdf"},  # Custom path
            ],
            "save_extraction": [
                {"pdf_path": None, "output_path": None},  # Default paths
                {"pdf_path": None, "output_path": "custom_output.json"},  # Custom output
            ]
        }
        
        # Define expected file types
        expected_file_types = ["pdf", "PDF"]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check function coverage gaps
            for function_name, expected_params in expected_parameters.items():
                coverage = self.get_parameter_coverage(engine_name, function_name)
                
                if coverage["total_parameter_combinations"] == 0:
                    gaps.append(CoverageGap(
                        gap_type="function",
                        engine_name=engine_name,
                        function_name=function_name,
                        priority="high",
                        recommendation=f"Add basic tests for {function_name} function"
                    ))
                else:
                    # Check parameter coverage
                    tested_params = coverage["unique_parameter_sets"]
                    missing_params = []
                    
                    for expected_param in expected_params:
                        if expected_param not in tested_params:
                            missing_params.append(expected_param)
                    
                    if missing_params:
                        gaps.append(CoverageGap(
                            gap_type="parameter",
                            engine_name=engine_name,
                            function_name=function_name,
                            missing_parameters=missing_params,
                            priority="medium",
                            recommendation=f"Test {function_name} with additional parameter combinations"
                        ))
            
            # Check file type coverage gaps
            file_coverage = self.get_file_type_coverage(engine_name)
            tested_file_types = set(file_coverage["tested_file_types"])
            missing_file_types = [ft for ft in expected_file_types if ft not in tested_file_types]
            
            if missing_file_types:
                gaps.append(CoverageGap(
                    gap_type="file_type",
                    engine_name=engine_name,
                    missing_file_types=missing_file_types,
                    priority="medium",
                    recommendation=f"Test {engine_name} with additional file types: {missing_file_types}"
                ))
        
        return gaps
    
    def generate_coverage_report(self, engine_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate comprehensive coverage report.
        
        Args:
            engine_name: Specific engine name, or None for all engines
            
        Returns:
            Coverage report data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get coverage summary
            if engine_name:
                cursor.execute('''
                    SELECT engine_name, function_name, total_parameters_tested, 
                           total_file_types_tested, last_test_timestamp, coverage_score
                    FROM coverage_summary 
                    WHERE engine_name = ?
                    ORDER BY coverage_score DESC
                ''', (engine_name,))
            else:
                cursor.execute('''
                    SELECT engine_name, function_name, total_parameters_tested, 
                           total_file_types_tested, last_test_timestamp, coverage_score
                    FROM coverage_summary 
                    ORDER BY engine_name, coverage_score DESC
                ''')
            
            summary_rows = cursor.fetchall()
            
            # Organize by engine
            engine_summaries = {}
            
            for row in summary_rows:
                eng_name = row[0]
                if eng_name not in engine_summaries:
                    engine_summaries[eng_name] = {
                        "engine_name": eng_name,
                        "functions": [],
                        "total_functions": 0,
                        "avg_coverage_score": 0.0,
                        "coverage_gaps": []
                    }
                
                engine_summaries[eng_name]["functions"].append({
                    "function_name": row[1],
                    "parameters_tested": row[2],
                    "file_types_tested": row[3],
                    "last_test": row[4],
                    "coverage_score": row[5]
                })
            
            # Calculate averages and identify gaps
            for eng_name, summary in engine_summaries.items():
                summary["total_functions"] = len(summary["functions"])
                
                if summary["functions"]:
                    summary["avg_coverage_score"] = sum(f["coverage_score"] for f in summary["functions"]) / len(summary["functions"])
                
                # Get coverage gaps
                summary["coverage_gaps"] = [asdict(gap) for gap in self.identify_coverage_gaps(eng_name)]
            
            # Generate overall statistics
            total_functions = sum(s["total_functions"] for s in engine_summaries.values())
            avg_coverage = sum(s["avg_coverage_score"] for s in engine_summaries.values()) / len(engine_summaries) if engine_summaries else 0
            
            report = {
                "report_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "scope": engine_name or "all_engines",
                "engine_summaries": engine_summaries,
                "overall_statistics": {
                    "total_engines": len(engine_summaries),
                    "total_functions": total_functions,
                    "average_coverage_score": avg_coverage,
                    "engines_with_gaps": len([s for s in engine_summaries.values() if s["coverage_gaps"]])
                },
                "recommendations": self._generate_recommendations(engine_summaries)
            }
            
            return report
    
    def _generate_recommendations(self, engine_summaries: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on coverage analysis."""
        recommendations = []
        
        for engine_name, summary in engine_summaries.items():
            avg_score = summary["avg_coverage_score"]
            
            if avg_score < 30:
                recommendations.append(f"CRITICAL: {engine_name} has very low test coverage ({avg_score:.1f}%). Add comprehensive tests.")
            elif avg_score < 60:
                recommendations.append(f"HIGH: {engine_name} needs more test coverage ({avg_score:.1f}%). Focus on parameter variations.")
            elif avg_score < 80:
                recommendations.append(f"MEDIUM: {engine_name} could benefit from additional test scenarios ({avg_score:.1f}%).")
            
            # Check for functions without recent tests
            for func in summary["functions"]:
                if func["last_test"]:
                    last_test = datetime.fromisoformat(func["last_test"].replace('Z', '+00:00'))
                    if datetime.now() - last_test > timedelta(days=30):
                        recommendations.append(f"Update tests for {engine_name}.{func['function_name']} (last tested {func['last_test']})")
        
        return recommendations
    
    def export_coverage_data(self, output_path: Optional[str] = None) -> str:
        """
        Export coverage data to JSON file.
        
        Args:
            output_path: Path to save export file
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            output_path = Path("output/engine_testing/coverage_export.json")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive report
        report = self.generate_coverage_report()
        
        # Add raw data
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Export parameter tests
            cursor.execute('SELECT * FROM parameter_tests ORDER BY test_timestamp DESC')
            param_tests = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            
            # Export file type tests
            cursor.execute('SELECT * FROM file_type_tests ORDER BY test_timestamp DESC')
            file_tests = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            
            report["raw_data"] = {
                "parameter_tests": param_tests,
                "file_type_tests": file_tests
            }
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Coverage data exported to: {output_path}")
        return str(output_path)


# Convenience functions
def track_parameter_test(engine_name: str, function_name: str, 
                        parameter_set: Dict[str, Any], test_success: bool,
                        execution_time: float, pdf_file: str, 
                        test_output_size: int, error_message: Optional[str] = None):
    """Track a parameter test result."""
    tracker = CoverageTracker()
    
    record = ParameterTestRecord(
        function_name=function_name,
        engine_name=engine_name,
        parameter_set=parameter_set,
        test_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        test_success=test_success,
        execution_time=execution_time,
        pdf_file=pdf_file,
        test_output_size=test_output_size,
        error_message=error_message
    )
    
    tracker.record_parameter_test(record)


def track_file_type_test(engine_name: str, file_type: str, file_path: str,
                        test_success: bool, extraction_time: float,
                        output_quality_score: Optional[float] = None,
                        error_message: Optional[str] = None):
    """Track a file type test result."""
    tracker = CoverageTracker()
    
    record = FileTypeTestRecord(
        engine_name=engine_name,
        file_type=file_type,
        file_path=file_path,
        test_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        test_success=test_success,
        extraction_time=extraction_time,
        output_quality_score=output_quality_score,
        error_message=error_message
    )
    
    tracker.record_file_type_test(record)


def generate_coverage_report(engine_name: Optional[str] = None) -> Dict[str, Any]:
    """Generate coverage report for engines."""
    tracker = CoverageTracker()
    return tracker.generate_coverage_report(engine_name)