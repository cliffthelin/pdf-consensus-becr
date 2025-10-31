#!/usr/bin/env python3
"""
Test Runner Widget

This module provides a GUI widget for running tests with real-time progress
tracking, results display, and integration with the test execution tracker.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QProgressBar, QLabel, QCheckBox, QGroupBox, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import QThread, Signal, QTimer, Qt
from PySide6.QtGui import QFont, QColor

try:
    from ..testing.test_execution_tracker import ExecutionTracker, SuiteExecutionResult
except ImportError:
    # Handle standalone execution by importing directly from the module path
    import sys
    from pathlib import Path
    
    # Add the src directory to sys.path
    current_file = Path(__file__).resolve()
    src_dir = current_file.parent.parent.parent / "src"
    
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    
    # Now import using the full module path
    from compareblocks.testing.test_execution_tracker import ExecutionTracker, SuiteExecutionResult


class TestRunnerThread(QThread):
    """Background thread for running tests without blocking the GUI."""
    
    progress_updated = Signal(str)  # Progress message
    test_completed = Signal(object)  # SuiteExecutionResult
    error_occurred = Signal(str)  # Error message
    
    def __init__(self, test_categories: Optional[List[str]] = None):
        super().__init__()
        self.test_categories = test_categories
        self.tracker = ExecutionTracker()
    
    def run(self):
        """Run tests in background thread."""
        try:
            self.progress_updated.emit("🔧 Initializing test execution...")
            
            # Run tests with tracking
            result = self.tracker.run_all_tests(self.test_categories)
            
            self.progress_updated.emit("✅ Test execution completed")
            self.test_completed.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(f"Test execution failed: {str(e)}")


class ExecutionResultsTable(QTableWidget):
    """Table widget for displaying individual test results."""
    
    def __init__(self):
        super().__init__()
        self.setup_table()
    
    def setup_table(self):
        """Setup the results table."""
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            'Test Name', 'Status', 'Duration (s)', 'File', 'Error'
        ])
        
        # Configure column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Test Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Duration
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # File
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Error
        
        # Enable sorting
        self.setSortingEnabled(True)
        
        # Alternate row colors
        self.setAlternatingRowColors(True)
    
    def update_results(self, test_results: List):
        """Update table with test results."""
        self.setRowCount(len(test_results))
        
        for row, result in enumerate(test_results):
            # Test name
            self.setItem(row, 0, QTableWidgetItem(result.test_name))
            
            # Status with color coding
            status_item = QTableWidgetItem(result.status.upper())
            if result.status == 'passed':
                status_item.setBackground(QColor(144, 238, 144))  # Light green
            elif result.status == 'failed':
                status_item.setBackground(QColor(255, 182, 193))  # Light red
            elif result.status == 'skipped':
                status_item.setBackground(QColor(255, 255, 224))  # Light yellow
            elif result.status == 'error':
                status_item.setBackground(QColor(255, 160, 122))  # Light orange
            
            self.setItem(row, 1, status_item)
            
            # Duration
            duration_item = QTableWidgetItem(f"{result.duration:.3f}")
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(row, 2, duration_item)
            
            # File
            file_item = QTableWidgetItem(result.test_file.split('/')[-1])  # Just filename
            self.setItem(row, 3, file_item)
            
            # Error message
            error_text = result.error_message[:100] + "..." if result.error_message and len(result.error_message) > 100 else (result.error_message or "")
            self.setItem(row, 4, QTableWidgetItem(error_text))


class TestRunnerWidget(QWidget):
    """Main test runner widget with GUI controls and results display."""
    
    def __init__(self):
        super().__init__()
        self.test_thread = None
        self.setup_ui()
        self.load_test_history()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("🧪 BECR Test Runner")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Test category selection
        category_group = QGroupBox("Test Categories")
        category_layout = QHBoxLayout(category_group)
        
        self.unit_checkbox = QCheckBox("Unit Tests")
        self.unit_checkbox.setChecked(True)
        self.integration_checkbox = QCheckBox("Integration Tests")
        self.integration_checkbox.setChecked(True)
        self.gui_checkbox = QCheckBox("GUI Tests")
        self.gui_checkbox.setChecked(True)
        
        category_layout.addWidget(self.unit_checkbox)
        category_layout.addWidget(self.integration_checkbox)
        category_layout.addWidget(self.gui_checkbox)
        category_layout.addStretch()
        
        layout.addWidget(category_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.run_all_button = QPushButton("🚀 Run All Tests")
        self.run_all_button.setMinimumHeight(40)
        self.run_all_button.clicked.connect(self.run_all_tests)
        
        self.run_selected_button = QPushButton("🎯 Run Selected Categories")
        self.run_selected_button.setMinimumHeight(40)
        self.run_selected_button.clicked.connect(self.run_selected_tests)
        
        self.stop_button = QPushButton("⏹️ Stop Tests")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_tests)
        
        button_layout.addWidget(self.run_all_button)
        button_layout.addWidget(self.run_selected_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to run tests")
        layout.addWidget(self.status_label)
        
        # Results splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Summary display
        summary_group = QGroupBox("Test Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_label = QLabel("No tests run yet")
        summary_layout.addWidget(self.summary_label)
        
        splitter.addWidget(summary_group)
        
        # Detailed results table
        results_group = QGroupBox("Detailed Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = ExecutionResultsTable()
        results_layout.addWidget(self.results_table)
        
        splitter.addWidget(results_group)
        
        # Set splitter proportions
        splitter.setSizes([100, 400])
        
        layout.addWidget(splitter)
        
        # Auto-refresh timer for progress updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(1000)  # Update every second
    
    def run_all_tests(self):
        """Run all tests."""
        self.run_tests(None)
    
    def run_selected_tests(self):
        """Run only selected test categories."""
        categories = []
        if self.unit_checkbox.isChecked():
            categories.append('unit')
        if self.integration_checkbox.isChecked():
            categories.append('integration')
        if self.gui_checkbox.isChecked():
            categories.append('gui')
        
        if not categories:
            QMessageBox.warning(self, "No Categories Selected", 
                              "Please select at least one test category to run.")
            return
        
        self.run_tests(categories)
    
    def run_tests(self, categories: Optional[List[str]]):
        """Start test execution in background thread."""
        if self.test_thread and self.test_thread.isRunning():
            QMessageBox.information(self, "Tests Running", 
                                  "Tests are already running. Please wait for completion.")
            return
        
        # Disable run buttons, enable stop button
        self.run_all_button.setEnabled(False)
        self.run_selected_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Update status
        category_text = "all categories" if not categories else ", ".join(categories)
        self.status_label.setText(f"🔧 Running tests for {category_text}...")
        
        # Start test thread
        self.test_thread = TestRunnerThread(categories)
        self.test_thread.progress_updated.connect(self.update_progress)
        self.test_thread.test_completed.connect(self.test_execution_completed)
        self.test_thread.error_occurred.connect(self.test_execution_error)
        self.test_thread.start()
    
    def stop_tests(self):
        """Stop running tests."""
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.terminate()
            self.test_thread.wait()
            self.test_execution_finished()
            self.status_label.setText("⏹️ Tests stopped by user")
    
    def update_progress(self, message: str):
        """Update progress display."""
        self.status_label.setText(message)
    
    def test_execution_completed(self, result: SuiteExecutionResult):
        """Handle successful test completion."""
        self.test_execution_finished()
        
        # Update summary
        summary_text = f"""
📊 Test Execution Summary
Total Tests: {result.total_tests}
✅ Passed: {result.passed}
❌ Failed: {result.failed}
⏭️ Skipped: {result.skipped}
💥 Errors: {result.errors}
⏱️ Duration: {result.total_duration:.2f}s
🕐 Completed: {datetime.fromisoformat(result.timestamp.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if result.coverage_percentage:
            summary_text += f"📈 Coverage: {result.coverage_percentage:.1f}%\n"
        
        self.summary_label.setText(summary_text)
        
        # Update results table
        self.results_table.update_results(result.test_results)
        
        # Update status
        if result.failed > 0 or result.errors > 0:
            self.status_label.setText(f"❌ Tests completed with {result.failed + result.errors} failures/errors")
        else:
            self.status_label.setText(f"✅ All {result.passed} tests passed successfully!")
    
    def test_execution_error(self, error_message: str):
        """Handle test execution error."""
        self.test_execution_finished()
        self.status_label.setText(f"❌ Test execution failed: {error_message}")
        QMessageBox.critical(self, "Test Execution Error", error_message)
    
    def test_execution_finished(self):
        """Clean up after test execution."""
        # Re-enable run buttons, disable stop button
        self.run_all_button.setEnabled(True)
        self.run_selected_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
    
    def refresh_status(self):
        """Refresh status display periodically."""
        # This could be used to show real-time updates if needed
        pass
    
    def load_test_history(self):
        """Load and display recent test history."""
        history_path = Path('output/test_execution_history.json')
        if not history_path.exists():
            return
        
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if history:
                # Show most recent result
                latest = history[-1]
                self.summary_label.setText(f"Last run: {latest['passed']}/{latest['total_tests']} passed")
        
        except Exception as e:
            print(f"Warning: Could not load test history: {e}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = TestRunnerWidget()
    widget.show()
    sys.exit(app.exec())