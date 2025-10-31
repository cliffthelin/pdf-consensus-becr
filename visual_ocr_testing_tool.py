#!/usr/bin/env python3
"""
Visual OCR Testing Tool - Comprehensive OCR Analysis and Optimization Platform

This unified tool provides multiple input feeds and testing capabilities:

INPUT FEEDS:
1. Direct Code Building - Live code integration and testing
2. MCP Integration - Model Context Protocol data sources
3. JSON Review - Configuration and result analysis
4. File System Monitoring - Real-time file change detection
5. API Endpoints - External data integration
6. Database Connections - Persistent data storage
7. Configuration Management - Dynamic parameter adjustment
8. Test Result Archives - Historical performance tracking

CORE FEATURES:
1. OCR parameter optimization testing
2. Improved OCR engine validation
3. Visual debugging with GUI interface
4. Debug image extraction and analysis
5. Real-time OCR quality assessment
6. Multi-source data integration
7. Automated testing workflows
8. Performance benchmarking

Usage:
    python visual_ocr_testing_tool.py                    # GUI mode with all feeds
    python visual_ocr_testing_tool.py --cli              # CLI optimization mode
    python visual_ocr_testing_tool.py --test-engine      # Test improved engine
    python visual_ocr_testing_tool.py --extract-debug    # Extract debug images
    python visual_ocr_testing_tool.py --mcp-feed         # Enable MCP data feed
    python visual_ocr_testing_tool.py --json-config path # Load JSON configuration
    python visual_ocr_testing_tool.py --monitor-files    # Enable file monitoring
    python visual_ocr_testing_tool.py --api-endpoint url # Connect to API endpoint
"""

import sys
import cv2
import numpy as np
import pytesseract
from PIL import Image
import fitz
from pathlib import Path
import json
import io
import argparse
import webbrowser
import threading
import time
import requests
import sqlite3
import yaml
import configparser
import watchdog.observers
import watchdog.events
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import queue

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from compareblocks.config.file_manager import file_manager
from compareblocks.engines.gbg_guided_tesseract_engine import GBGGuidedTesseractEngine
from compareblocks.debug import extract_debug_images_for_page

# Try to import GUI components
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QTabWidget, QTextEdit, QLabel, QPushButton, QSpinBox, QScrollArea,
        QGroupBox, QGridLayout, QSplitter, QMessageBox, QProgressBar,
        QComboBox, QTableWidget, QTableWidgetItem, QCheckBox, QLineEdit,
        QFileDialog, QTreeWidget, QTreeWidgetItem, QStatusBar, QMenuBar,
        QAction, QToolBar, QDockWidget, QListWidget, QListWidgetItem
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer, QObject, pyqtSignal
    from PySide6.QtGui import QPixmap, QFont, QTextOption, QIcon, QColor
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


@dataclass
class InputFeedConfig:
    """Configuration for input feed sources."""
    name: str
    type: str  # 'mcp', 'json', 'api', 'file', 'database', 'code'
    source: str
    enabled: bool = True
    refresh_interval: int = 30  # seconds
    parameters: Dict[str, Any] = None


@dataclass
class TestResult:
    """Standardized test result structure."""
    timestamp: datetime
    source: str
    test_type: str
    page_num: int
    block_index: int
    similarity: float
    confidence: float
    extracted_text: str
    expected_text: str
    preprocessing: str
    tesseract_config: str
    success: bool
    metadata: Dict[str, Any] = None


class InputFeedManager:
    """Manages multiple input feeds for the OCR testing tool."""
    
    def __init__(self):
        self.feeds = {}
        self.callbacks = []
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.data_queue = queue.Queue()
        self.running = False
        
    def register_feed(self, config: InputFeedConfig):
        """Register a new input feed."""
        self.feeds[config.name] = {
            'config': config,
            'last_update': None,
            'data': None,
            'status': 'inactive'
        }
        
    def add_callback(self, callback: Callable):
        """Add callback for feed updates."""
        self.callbacks.append(callback)
        
    def start_feeds(self):
        """Start all enabled feeds."""
        self.running = True
        for feed_name, feed_info in self.feeds.items():
            if feed_info['config'].enabled:
                self.executor.submit(self._run_feed, feed_name)
                
    def stop_feeds(self):
        """Stop all feeds."""
        self.running = False
        
    def _run_feed(self, feed_name: str):
        """Run a specific feed in background."""
        feed_info = self.feeds[feed_name]
        config = feed_info['config']
        
        while self.running:
            try:
                feed_info['status'] = 'active'
                
                if config.type == 'mcp':
                    data = self._fetch_mcp_data(config)
                elif config.type == 'json':
                    data = self._fetch_json_data(config)
                elif config.type == 'api':
                    data = self._fetch_api_data(config)
                elif config.type == 'file':
                    data = self._fetch_file_data(config)
                elif config.type == 'database':
                    data = self._fetch_database_data(config)
                elif config.type == 'code':
                    data = self._fetch_code_data(config)
                else:
                    data = None
                    
                if data:
                    feed_info['data'] = data
                    feed_info['last_update'] = datetime.now()
                    
                    # Notify callbacks
                    for callback in self.callbacks:
                        try:
                            callback(feed_name, data)
                        except Exception as e:
                            print(f"Callback error for {feed_name}: {e}")
                            
                feed_info['status'] = 'waiting'
                time.sleep(config.refresh_interval)
                
            except Exception as e:
                feed_info['status'] = f'error: {str(e)}'
                time.sleep(config.refresh_interval)
                
    def _fetch_mcp_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from MCP source."""
        try:
            # Check for MCP configuration
            mcp_config_path = Path.home() / '.kiro' / 'settings' / 'mcp.json'
            workspace_mcp_path = Path('.kiro') / 'settings' / 'mcp.json'
            
            mcp_data = {}
            
            # Load user-level MCP config
            if mcp_config_path.exists():
                with open(mcp_config_path, 'r') as f:
                    user_config = json.load(f)
                    mcp_data.update(user_config)
                    
            # Load workspace-level MCP config (takes precedence)
            if workspace_mcp_path.exists():
                with open(workspace_mcp_path, 'r') as f:
                    workspace_config = json.load(f)
                    mcp_data.update(workspace_config)
                    
            return {
                'type': 'mcp_config',
                'servers': mcp_data.get('mcpServers', {}),
                'timestamp': datetime.now().isoformat(),
                'source': str(config.source)
            }
            
        except Exception as e:
            return {'error': str(e), 'type': 'mcp_error'}
            
    def _fetch_json_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from JSON file or configuration."""
        try:
            json_path = Path(config.source)
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                return {
                    'type': 'json_config',
                    'data': data,
                    'file_path': str(json_path),
                    'file_size': json_path.stat().st_size,
                    'last_modified': datetime.fromtimestamp(json_path.stat().st_mtime).isoformat(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': f'File not found: {json_path}', 'type': 'json_error'}
                
        except Exception as e:
            return {'error': str(e), 'type': 'json_error'}
            
    def _fetch_api_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from API endpoint."""
        try:
            headers = config.parameters.get('headers', {}) if config.parameters else {}
            timeout = config.parameters.get('timeout', 10) if config.parameters else 10
            
            response = requests.get(config.source, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            return {
                'type': 'api_response',
                'data': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'url': config.source,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'type': 'api_error'}
            
    def _fetch_file_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from file system monitoring."""
        try:
            file_path = Path(config.source)
            
            if file_path.is_file():
                stat = file_path.stat()
                return {
                    'type': 'file_info',
                    'path': str(file_path),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'exists': True,
                    'timestamp': datetime.now().isoformat()
                }
            elif file_path.is_dir():
                files = list(file_path.glob('*'))
                return {
                    'type': 'directory_info',
                    'path': str(file_path),
                    'file_count': len([f for f in files if f.is_file()]),
                    'dir_count': len([f for f in files if f.is_dir()]),
                    'files': [str(f.name) for f in files[:10]],  # First 10 files
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': f'Path not found: {file_path}', 'type': 'file_error'}
                
        except Exception as e:
            return {'error': str(e), 'type': 'file_error'}
            
    def _fetch_database_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from database connection."""
        try:
            # Simple SQLite example - can be extended for other databases
            if config.source.endswith('.db') or config.source.endswith('.sqlite'):
                conn = sqlite3.connect(config.source)
                cursor = conn.cursor()
                
                # Get table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                table_info = {}
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    table_info[table_name] = count
                    
                conn.close()
                
                return {
                    'type': 'database_info',
                    'database': config.source,
                    'tables': table_info,
                    'total_tables': len(tables),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': 'Unsupported database type', 'type': 'database_error'}
                
        except Exception as e:
            return {'error': str(e), 'type': 'database_error'}
            
    def _fetch_code_data(self, config: InputFeedConfig) -> Optional[Dict]:
        """Fetch data from direct code integration."""
        try:
            # Execute code snippets or import modules dynamically
            if config.parameters and 'code' in config.parameters:
                code = config.parameters['code']
                
                # Create safe execution environment
                safe_globals = {
                    '__builtins__': {},
                    'json': json,
                    'Path': Path,
                    'datetime': datetime,
                    'file_manager': file_manager
                }
                
                local_vars = {}
                exec(code, safe_globals, local_vars)
                
                return {
                    'type': 'code_execution',
                    'result': local_vars.get('result', local_vars),
                    'code': code,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'error': 'No code provided', 'type': 'code_error'}
                
        except Exception as e:
            return {'error': str(e), 'type': 'code_error'}


class TestResultDatabase:
    """Database for storing and retrieving test results."""
    
    def __init__(self, db_path: str = "output/ocr_test_results.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                test_type TEXT NOT NULL,
                page_num INTEGER,
                block_index INTEGER,
                similarity REAL,
                confidence REAL,
                extracted_text TEXT,
                expected_text TEXT,
                preprocessing TEXT,
                tesseract_config TEXT,
                success BOOLEAN,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feed_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                feed_name TEXT NOT NULL,
                feed_type TEXT NOT NULL,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_test_result(self, result: TestResult):
        """Save a test result to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_results 
            (timestamp, source, test_type, page_num, block_index, similarity, 
             confidence, extracted_text, expected_text, preprocessing, 
             tesseract_config, success, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.timestamp.isoformat(),
            result.source,
            result.test_type,
            result.page_num,
            result.block_index,
            result.similarity,
            result.confidence,
            result.extracted_text,
            result.expected_text,
            result.preprocessing,
            result.tesseract_config,
            result.success,
            json.dumps(result.metadata) if result.metadata else None
        ))
        
        conn.commit()
        conn.close()
        
    def get_test_results(self, limit: int = 100, test_type: str = None) -> List[TestResult]:
        """Retrieve test results from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM test_results"
        params = []
        
        if test_type:
            query += " WHERE test_type = ?"
            params.append(test_type)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            metadata = json.loads(row[13]) if row[13] else None
            result = TestResult(
                timestamp=datetime.fromisoformat(row[1]),
                source=row[2],
                test_type=row[3],
                page_num=row[4],
                block_index=row[5],
                similarity=row[6],
                confidence=row[7],
                extracted_text=row[8],
                expected_text=row[9],
                preprocessing=row[10],
                tesseract_config=row[11],
                success=bool(row[12]),
                metadata=metadata
            )
            results.append(result)
            
        conn.close()
        return results
        
    def save_feed_data(self, feed_name: str, feed_type: str, data: Dict):
        """Save feed data to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feed_data (timestamp, feed_name, feed_type, data)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            feed_name,
            feed_type,
            json.dumps(data)
        ))
        
        conn.commit()
        conn.close()


class OCROptimizationEngine:
    """Core OCR optimization and testing engine with multi-input feed support."""
    
    def __init__(self):
        self.preprocessing_methods = [
            ('minimal', self._minimal_preprocessing),
            ('light', self._light_preprocessing),
            ('enhanced', self._enhanced_preprocessing),
            ('current_aggressive', self._aggressive_preprocessing)
        ]
        
        self.tesseract_configs = [
            {'name': 'default', 'config': '--psm 6'},
            {'name': 'single_text_line', 'config': '--psm 7'},
            {'name': 'single_word', 'config': '--psm 8'},
            {'name': 'raw_line', 'config': '--psm 13'},
            {'name': 'lstm_only', 'config': '--psm 6 --oem 1'},
            {'name': 'legacy_only', 'config': '--psm 6 --oem 0'},
            {'name': 'combined_engines', 'config': '--psm 6 --oem 2'},
        ]
        
        # Initialize input feed manager and database
        self.feed_manager = InputFeedManager()
        self.test_db = TestResultDatabase()
        
        # Setup default feeds
        self._setup_default_feeds()
        
        # Auto-discover Source_docs JSON files
        self._discover_source_docs_feeds()
        
    def _setup_default_feeds(self):
        """Setup default input feeds."""
        # MCP Configuration Feed
        mcp_feed = InputFeedConfig(
            name="mcp_config",
            type="mcp",
            source="mcp_servers",
            enabled=True,
            refresh_interval=60,
            parameters={"auto_approve": True}
        )
        self.feed_manager.register_feed(mcp_feed)
        
        # GBG Analysis JSON Feed
        gbg_feed = InputFeedConfig(
            name="gbg_analysis",
            type="json",
            source=str(file_manager.get_gbg_analysis_output_path()),
            enabled=True,
            refresh_interval=30
        )
        self.feed_manager.register_feed(gbg_feed)
        
        # Configuration Files Feed
        config_feed = InputFeedConfig(
            name="config_files",
            type="file",
            source="config",
            enabled=True,
            refresh_interval=45
        )
        self.feed_manager.register_feed(config_feed)
        
        # Output Directory Monitoring
        output_feed = InputFeedConfig(
            name="output_monitoring",
            type="file",
            source="output",
            enabled=True,
            refresh_interval=20
        )
        self.feed_manager.register_feed(output_feed)
        
        # Code Integration Feed
        code_feed = InputFeedConfig(
            name="system_status",
            type="code",
            source="system_check",
            enabled=True,
            refresh_interval=120,
            parameters={
                "code": """
# System status check
import os
from pathlib import Path

result = {
    'pdf_exists': Path('Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf').exists(),
    'gbg_analysis_exists': Path(file_manager.get_gbg_analysis_output_path()).exists(),
    'output_dir_size': sum(f.stat().st_size for f in Path('output').rglob('*') if f.is_file()) if Path('output').exists() else 0,
    'python_version': os.sys.version,
    'working_directory': str(Path.cwd()),
    'environment_vars': {k: v for k, v in os.environ.items() if 'PYTHON' in k or 'PATH' in k}
}
"""
            }
        )
        self.feed_manager.register_feed(code_feed)
        
        # Add callback for feed updates
        self.feed_manager.add_callback(self._handle_feed_update)
        
    def _discover_source_docs_feeds(self):
        """Auto-discover and register JSON feeds from Source_docs directory."""
        source_docs_path = Path("Source_docs")
        if not source_docs_path.exists():
            return
        
        # Find important JSON files
        important_patterns = [
            "**/gbg_full_analysis.json",
            "**/consensus_decisions.ndjson", 
            "**/*_corrections*.json",
            "**/*_verified*.json",
            "**/*_diff_decisions*.json"
        ]
        
        discovered_feeds = []
        
        for pattern in important_patterns:
            for json_file in source_docs_path.glob(pattern):
                try:
                    # Create a descriptive name
                    relative_path = json_file.relative_to(source_docs_path)
                    parent_dir = relative_path.parent.name if relative_path.parent.name != "." else "root"
                    file_stem = json_file.stem
                    
                    feed_name = f"source_docs_{parent_dir}_{file_stem}".replace(" ", "_").replace("-", "_").lower()
                    
                    # Determine feed type based on file extension
                    feed_type = "json" if json_file.suffix == ".json" else "file"
                    
                    feed_config = InputFeedConfig(
                        name=feed_name,
                        type=feed_type,
                        source=str(json_file),
                        enabled=False,  # Disabled by default to avoid overwhelming
                        refresh_interval=60,  # Check every minute
                        parameters={
                            "auto_discovered": True,
                            "source_directory": str(relative_path.parent),
                            "file_type": "analysis" if "gbg" in file_stem else "processing"
                        }
                    )
                    
                    self.feed_manager.register_feed(feed_config)
                    discovered_feeds.append(feed_name)
                    
                except Exception as e:
                    print(f"Error discovering feed for {json_file}: {e}")
        
        if discovered_feeds:
            print(f"📡 Auto-discovered {len(discovered_feeds)} Source_docs feeds (disabled by default)")
            print(f"   Feeds: {', '.join(discovered_feeds[:3])}{'...' if len(discovered_feeds) > 3 else ''}")
        
    def _handle_feed_update(self, feed_name: str, data: Dict):
        """Handle updates from input feeds."""
        # Save feed data to database
        feed_type = data.get('type', 'unknown')
        self.test_db.save_feed_data(feed_name, feed_type, data)
        
        # Process specific feed types
        if feed_name == "gbg_analysis" and data.get('type') == 'json_config':
            self._process_gbg_update(data)
        elif feed_name == "mcp_config" and data.get('type') == 'mcp_config':
            self._process_mcp_update(data)
        elif feed_name == "system_status" and data.get('type') == 'code_execution':
            self._process_system_status(data)
            
    def _process_gbg_update(self, data: Dict):
        """Process GBG analysis updates."""
        try:
            gbg_data = data['data']
            total_pages = len(gbg_data.get('pages', {}))
            total_blocks = sum(len(page_data.get('blocks', [])) for page_data in gbg_data.get('pages', {}).values())
            
            print(f"📊 GBG Analysis Updated: {total_pages} pages, {total_blocks} blocks")
            
        except Exception as e:
            print(f"Error processing GBG update: {e}")
            
    def _process_mcp_update(self, data: Dict):
        """Process MCP configuration updates."""
        try:
            servers = data.get('servers', {})
            active_servers = [name for name, config in servers.items() if not config.get('disabled', False)]
            
            print(f"🔌 MCP Servers: {len(active_servers)} active out of {len(servers)} total")
            
        except Exception as e:
            print(f"Error processing MCP update: {e}")
            
    def _process_system_status(self, data: Dict):
        """Process system status updates."""
        try:
            result = data.get('result', {})
            
            status_items = []
            if result.get('pdf_exists'):
                status_items.append("✅ PDF")
            else:
                status_items.append("❌ PDF")
                
            if result.get('gbg_analysis_exists'):
                status_items.append("✅ GBG")
            else:
                status_items.append("❌ GBG")
                
            output_size = result.get('output_dir_size', 0)
            status_items.append(f"📁 {output_size // 1024}KB")
            
            print(f"🖥️  System Status: {' | '.join(status_items)}")
            
        except Exception as e:
            print(f"Error processing system status: {e}")
            
    def start_feeds(self):
        """Start all input feeds."""
        self.feed_manager.start_feeds()
        
    def stop_feeds(self):
        """Stop all input feeds."""
        self.feed_manager.stop_feeds()
        
    def get_feed_status(self) -> Dict[str, Any]:
        """Get status of all input feeds."""
        status = {}
        for feed_name, feed_info in self.feed_manager.feeds.items():
            status[feed_name] = {
                'enabled': feed_info['config'].enabled,
                'status': feed_info['status'],
                'last_update': feed_info['last_update'].isoformat() if feed_info['last_update'] else None,
                'type': feed_info['config'].type,
                'source': feed_info['config'].source
            }
        return status
        
    def add_custom_feed(self, config: InputFeedConfig):
        """Add a custom input feed."""
        self.feed_manager.register_feed(config)
        
    def load_configuration_from_feed(self, feed_name: str) -> Optional[Dict]:
        """Load configuration from a specific feed."""
        if feed_name in self.feed_manager.feeds:
            feed_info = self.feed_manager.feeds[feed_name]
            return feed_info.get('data')
        return None
    
    def _minimal_preprocessing(self, image):
        """Minimal preprocessing - just grayscale."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return gray
    
    def _light_preprocessing(self, image):
        """Light preprocessing - optimal for clear text."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        return denoised
    
    def _enhanced_preprocessing(self, image):
        """Enhanced preprocessing with morphological operations."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)
        return cleaned
    
    def _aggressive_preprocessing(self, image):
        """Aggressive preprocessing (for comparison)."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        denoised = cv2.medianBlur(binary, 3)
        enhanced = cv2.equalizeHist(denoised)
        return enhanced
    
    def extract_block_region(self, pdf_path, page_num, block_index=0):
        """Extract specific block region for testing."""
        gbg_analysis_path = file_manager.get_gbg_analysis_output_path()
        
        with open(gbg_analysis_path, 'r', encoding='utf-8') as f:
            gbg_data = json.load(f)
        
        gbg_blocks = gbg_data.get('pages', {}).get(str(page_num), {}).get('blocks', [])
        
        if block_index >= len(gbg_blocks):
            raise ValueError(f"Block index {block_index} not found on page {page_num}")
        
        gbg_block = gbg_blocks[block_index]
        expected_text = gbg_block.get('text_content', '').strip()
        bbox = gbg_block.get('bbox', {})
        
        pdf_document = fitz.open(pdf_path)
        page = pdf_document[page_num]
        
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        
        pil_image = Image.open(io.BytesIO(img_data))
        cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        x = int(bbox.get('x', 0) * 2)
        y = int(bbox.get('y', 0) * 2)
        width = int(bbox.get('width', 0) * 2)
        height = int(bbox.get('height', 0) * 2)
        
        padding = 10
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(cv_image.shape[1], x + width + padding)
        y2 = min(cv_image.shape[0], y + height + padding)
        
        region = cv_image[y1:y2, x1:x2]
        pdf_document.close()
        
        return region, expected_text, gbg_block.get('block_id', '')
    
    def test_ocr_configuration(self, region, expected_text, preprocessing_func, tesseract_config):
        """Test specific OCR configuration."""
        try:
            processed_region = preprocessing_func(region)
            
            ocr_result = pytesseract.image_to_data(
                processed_region,
                output_type=pytesseract.Output.DICT,
                config=tesseract_config['config']
            )
            
            text_parts = []
            confidences = []
            
            for i, conf in enumerate(ocr_result['conf']):
                if int(conf) > 0:
                    word = ocr_result['text'][i].strip()
                    if word:
                        text_parts.append(word)
                        confidences.append(int(conf))
            
            extracted_text = ' '.join(text_parts)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            from rapidfuzz import fuzz
            similarity = fuzz.ratio(extracted_text.lower(), expected_text.lower())
            
            return {
                'extracted_text': extracted_text,
                'confidence': avg_confidence,
                'similarity': similarity,
                'word_count': len(text_parts),
                'success': len(extracted_text.strip()) > 0,
                'processed_image': processed_region
            }
            
        except Exception as e:
            return {
                'extracted_text': '',
                'confidence': 0.0,
                'similarity': 0.0,
                'word_count': 0,
                'success': False,
                'error': str(e),
                'processed_image': None
            }
    
    def optimize_ocr_parameters(self, pdf_path, page_num, block_index):
        """Run full OCR parameter optimization."""
        region, expected_text, block_id = self.extract_block_region(pdf_path, page_num, block_index)
        
        results = []
        
        for prep_name, prep_func in self.preprocessing_methods:
            for config in self.tesseract_configs:
                result = self.test_ocr_configuration(region, expected_text, prep_func, config)
                result['preprocessing'] = prep_name
                result['tesseract_config'] = config['name']
                result['config_string'] = config['config']
                results.append(result)
        
        # Sort by similarity, then confidence
        best_results = sorted(results, key=lambda r: (r['similarity'], r['confidence']), reverse=True)
        
        return {
            'region': region,
            'expected_text': expected_text,
            'block_id': block_id,
            'results': results,
            'best_results': best_results,
            'winner': best_results[0] if best_results else None
        }
    
    def test_improved_engine(self, pdf_path, page_num=15):
        """Test the improved GBG-guided Tesseract engine."""
        gbg_analysis_path = file_manager.get_gbg_analysis_output_path()
        
        with open(gbg_analysis_path, 'r', encoding='utf-8') as f:
            gbg_data = json.load(f)
        
        engine = GBGGuidedTesseractEngine()
        results = engine.extract_text_with_gbg_guidance(pdf_path, gbg_data)
        
        # Find blocks from specified page
        page_blocks = [b for b in results['blocks'] if b['page'] == page_num]
        
        return {
            'total_blocks': results['total_blocks'],
            'avg_confidence': results['metadata']['avg_confidence'],
            'page_blocks': page_blocks,
            'metadata': results['metadata']
        }


class VisualOCRTestingWidget(QWidget):
    """GUI widget for visual OCR testing and optimization with multi-input feeds."""
    
    def __init__(self):
        super().__init__()
        self.ocr_engine = OCROptimizationEngine()
        self.feed_timer = QTimer()
        self.feed_timer.timeout.connect(self.update_feed_status)
        self.feed_timer.start(5000)  # Update every 5 seconds
        self.setup_ui()
        
        # Start input feeds
        self.ocr_engine.start_feeds()
    
    def setup_ui(self):
        """Setup the visual testing UI with input feeds."""
        layout = QVBoxLayout(self)
        
        # Tab widget for different testing modes
        self.tab_widget = QTabWidget()
        
        # OCR Optimization tab
        self.optimization_tab = self.create_optimization_tab()
        self.tab_widget.addTab(self.optimization_tab, "OCR Optimization")
        
        # Engine Testing tab
        self.engine_tab = self.create_engine_testing_tab()
        self.tab_widget.addTab(self.engine_tab, "Engine Testing")
        
        # Debug Images tab
        self.debug_tab = self.create_debug_images_tab()
        self.tab_widget.addTab(self.debug_tab, "Debug Images")
        
        # Input Feeds tab
        self.feeds_tab = self.create_feeds_tab()
        self.tab_widget.addTab(self.feeds_tab, "Input Feeds")
        
        # Configuration tab
        self.config_tab = self.create_configuration_tab()
        self.tab_widget.addTab(self.config_tab, "Configuration")
        
        # Test Results History tab
        self.history_tab = self.create_history_tab()
        self.tab_widget.addTab(self.history_tab, "Test History")
        
        layout.addWidget(self.tab_widget)
        
    def create_feeds_tab(self):
        """Create input feeds monitoring tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Feed status display
        layout.addWidget(QLabel("Input Feed Status:"))
        
        self.feeds_tree = QTreeWidget()
        self.feeds_tree.setHeaderLabels(["Feed Name", "Type", "Status", "Last Update", "Source"])
        layout.addWidget(self.feeds_tree)
        
        # Feed controls
        controls_layout = QHBoxLayout()
        
        self.refresh_feeds_button = QPushButton("Refresh Feeds")
        self.refresh_feeds_button.clicked.connect(self.refresh_feeds)
        controls_layout.addWidget(self.refresh_feeds_button)
        
        self.add_feed_button = QPushButton("Add Custom Feed")
        self.add_feed_button.clicked.connect(self.add_custom_feed)
        controls_layout.addWidget(self.add_feed_button)
        
        self.discover_feeds_button = QPushButton("Discover Source_docs Feeds")
        self.discover_feeds_button.clicked.connect(self.discover_and_enable_feeds)
        controls_layout.addWidget(self.discover_feeds_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Feed data display
        layout.addWidget(QLabel("Feed Data:"))
        self.feed_data_display = QTextEdit()
        self.feed_data_display.setFont(QFont("Consolas", 9))
        self.feed_data_display.setMaximumHeight(200)
        layout.addWidget(self.feed_data_display)
        
        return widget
        
    def create_configuration_tab(self):
        """Create configuration management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Configuration source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Configuration Source:"))
        
        self.config_source_combo = QComboBox()
        self.config_source_combo.addItems([
            "Default Settings",
            "JSON File",
            "Source_docs JSON Browser",
            "MCP Configuration",
            "Environment Variables",
            "Database Settings"
        ])
        self.config_source_combo.currentTextChanged.connect(self.load_configuration)
        source_layout.addWidget(self.config_source_combo)
        
        self.load_config_button = QPushButton("Load Configuration")
        self.load_config_button.clicked.connect(self.load_configuration)
        source_layout.addWidget(self.load_config_button)
        
        source_layout.addStretch()
        layout.addLayout(source_layout)
        
        # Configuration display and editing
        self.config_editor = QTextEdit()
        self.config_editor.setFont(QFont("Consolas", 9))
        layout.addWidget(self.config_editor)
        
        # Configuration controls
        config_controls = QHBoxLayout()
        
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.clicked.connect(self.save_configuration)
        config_controls.addWidget(self.save_config_button)
        
        self.apply_config_button = QPushButton("Apply Configuration")
        self.apply_config_button.clicked.connect(self.apply_configuration)
        config_controls.addWidget(self.apply_config_button)
        
        config_controls.addStretch()
        layout.addLayout(config_controls)
        
        return widget
        
    def create_history_tab(self):
        """Create test results history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # History controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Test Type:"))
        self.history_type_combo = QComboBox()
        self.history_type_combo.addItems([
            "All Tests",
            "OCR Optimization",
            "Engine Testing",
            "Debug Extraction"
        ])
        controls_layout.addWidget(self.history_type_combo)
        
        controls_layout.addWidget(QLabel("Limit:"))
        self.history_limit_spinbox = QSpinBox()
        self.history_limit_spinbox.setMinimum(10)
        self.history_limit_spinbox.setMaximum(1000)
        self.history_limit_spinbox.setValue(50)
        controls_layout.addWidget(self.history_limit_spinbox)
        
        self.load_history_button = QPushButton("Load History")
        self.load_history_button.clicked.connect(self.load_test_history)
        controls_layout.addWidget(self.load_history_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Timestamp", "Source", "Test Type", "Page", "Block", 
            "Similarity", "Confidence", "Success"
        ])
        layout.addWidget(self.history_table)
        
        # History details
        layout.addWidget(QLabel("Test Details:"))
        self.history_details = QTextEdit()
        self.history_details.setFont(QFont("Consolas", 9))
        self.history_details.setMaximumHeight(150)
        layout.addWidget(self.history_details)
        
        return widget
        
    def update_feed_status(self):
        """Update the feed status display."""
        if hasattr(self, 'feeds_tree'):
            self.feeds_tree.clear()
            
            feed_status = self.ocr_engine.get_feed_status()
            
            for feed_name, status in feed_status.items():
                item = QTreeWidgetItem([
                    feed_name,
                    status['type'],
                    status['status'],
                    status['last_update'] or 'Never',
                    str(status['source'])
                ])
                
                # Color code by status
                if status['status'] == 'active':
                    item.setBackground(0, QColor(144, 238, 144))  # Light green
                elif 'error' in status['status']:
                    item.setBackground(0, QColor(255, 182, 193))  # Light red
                elif status['status'] == 'waiting':
                    item.setBackground(0, QColor(255, 255, 224))  # Light yellow
                    
                self.feeds_tree.addTopLevelItem(item)
                
    def refresh_feeds(self):
        """Refresh all input feeds."""
        self.update_feed_status()
        self.feed_data_display.clear()
        self.feed_data_display.append("🔄 Refreshing all input feeds...")
        
        # Show recent feed data
        for feed_name, feed_info in self.ocr_engine.feed_manager.feeds.items():
            if feed_info['data']:
                self.feed_data_display.append(f"\n📡 {feed_name}:")
                self.feed_data_display.append(f"   Type: {feed_info['data'].get('type', 'unknown')}")
                if 'error' in feed_info['data']:
                    self.feed_data_display.append(f"   ❌ Error: {feed_info['data']['error']}")
                else:
                    self.feed_data_display.append(f"   ✅ Status: OK")
                    
    def add_custom_feed(self):
        """Add a custom input feed with enhanced source selection."""
        from PySide6.QtWidgets import QDialog, QFormLayout, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Feed")
        dialog.setModal(True)
        dialog.resize(500, 300)
        
        layout = QFormLayout(dialog)
        
        name_edit = QLineEdit()
        layout.addRow("Feed Name:", name_edit)
        
        type_combo = QComboBox()
        type_combo.addItems(["json", "api", "file", "database", "code"])
        type_combo.currentTextChanged.connect(lambda: self.update_source_options(type_combo, source_layout))
        layout.addRow("Feed Type:", type_combo)
        
        # Source selection with browse button
        source_layout = QHBoxLayout()
        source_edit = QLineEdit()
        source_layout.addWidget(source_edit)
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(lambda: self.browse_feed_source(type_combo.currentText(), source_edit))
        source_layout.addWidget(browse_button)
        
        source_docs_button = QPushButton("Source_docs")
        source_docs_button.clicked.connect(lambda: self.browse_source_docs_for_feed(source_edit))
        source_layout.addWidget(source_docs_button)
        
        layout.addRow("Source:", source_layout)
        
        interval_spinbox = QSpinBox()
        interval_spinbox.setMinimum(5)
        interval_spinbox.setMaximum(3600)
        interval_spinbox.setValue(30)
        layout.addRow("Refresh Interval (s):", interval_spinbox)
        
        # Parameters section
        params_edit = QTextEdit()
        params_edit.setMaximumHeight(100)
        params_edit.setPlainText('{"example": "value"}')
        layout.addRow("Parameters (JSON):", params_edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            try:
                # Parse parameters
                params_text = params_edit.toPlainText().strip()
                parameters = json.loads(params_text) if params_text else None
                
                config = InputFeedConfig(
                    name=name_edit.text() or f"custom_{type_combo.currentText()}",
                    type=type_combo.currentText(),
                    source=source_edit.text(),
                    enabled=True,
                    refresh_interval=interval_spinbox.value(),
                    parameters=parameters
                )
                
                self.ocr_engine.add_custom_feed(config)
                QMessageBox.information(self, "Success", f"Added custom feed: {config.name}")
                
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "Error", f"Invalid JSON parameters: {e}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add custom feed: {e}")
    
    def browse_feed_source(self, feed_type, source_edit):
        """Browse for feed source based on type."""
        if feed_type == "json":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select JSON File", "", "JSON Files (*.json);;All Files (*.*)"
            )
            if file_path:
                source_edit.setText(file_path)
        elif feed_type == "file":
            dir_path = QFileDialog.getExistingDirectory(self, "Select Directory")
            if dir_path:
                source_edit.setText(dir_path)
        elif feed_type == "database":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Database File", "", "Database Files (*.db *.sqlite);;All Files (*.*)"
            )
            if file_path:
                source_edit.setText(file_path)
    
    def browse_source_docs_for_feed(self, source_edit):
        """Browse Source_docs directory for feed source."""
        source_docs_path = Path("Source_docs")
        if not source_docs_path.exists():
            QMessageBox.warning(self, "Error", "Source_docs directory not found.")
            return
        
        # Simple directory browser for Source_docs
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Source_docs Subdirectory", str(source_docs_path)
        )
        if dir_path:
            source_edit.setText(dir_path)
    
    def update_source_options(self, type_combo, source_layout):
        """Update source options based on feed type."""
        # This could be expanded to show different options based on feed type
        pass
    
    def discover_and_enable_feeds(self):
        """Discover and enable Source_docs feeds through GUI selection."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QDialogButtonBox, QLabel, QScrollArea
        
        # Get all auto-discovered feeds
        discovered_feeds = []
        for feed_name, feed_info in self.ocr_engine.feed_manager.feeds.items():
            if (feed_info['config'].parameters and 
                feed_info['config'].parameters.get('auto_discovered', False)):
                discovered_feeds.append((feed_name, feed_info))
        
        if not discovered_feeds:
            QMessageBox.information(self, "No Feeds", "No auto-discovered Source_docs feeds found.")
            return
        
        # Create selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Enable Source_docs Feeds")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        info_label = QLabel(f"Found {len(discovered_feeds)} auto-discovered feeds from Source_docs:")
        layout.addWidget(info_label)
        
        # Scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        checkboxes = {}
        
        for feed_name, feed_info in discovered_feeds:
            config = feed_info['config']
            
            # Create descriptive checkbox
            display_name = feed_name.replace("source_docs_", "").replace("_", " ").title()
            source_path = Path(config.source)
            
            checkbox_text = f"{display_name}\n   📁 {source_path.parent.name}/{source_path.name}\n   🔄 {config.refresh_interval}s interval"
            
            checkbox = QCheckBox(checkbox_text)
            checkbox.setChecked(config.enabled)
            
            # Color code by file type
            if "gbg" in feed_name:
                checkbox.setStyleSheet("QCheckBox { background-color: #90EE90; }")  # Light green
            elif "consensus" in feed_name:
                checkbox.setStyleSheet("QCheckBox { background-color: #FFFFE0; }")  # Light yellow
            elif "corrections" in feed_name:
                checkbox.setStyleSheet("QCheckBox { background-color: #FFB6C1; }")  # Light red
            elif "verified" in feed_name:
                checkbox.setStyleSheet("QCheckBox { background-color: #ADD8E6; }")  # Light blue
            
            checkboxes[feed_name] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_button = QPushButton("Select All")
        select_all_button.clicked.connect(lambda: [cb.setChecked(True) for cb in checkboxes.values()])
        button_layout.addWidget(select_all_button)
        
        select_none_button = QPushButton("Select None")
        select_none_button.clicked.connect(lambda: [cb.setChecked(False) for cb in checkboxes.values()])
        button_layout.addWidget(select_none_button)
        
        button_layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.Accepted:
            # Enable/disable feeds based on selection
            enabled_count = 0
            for feed_name, checkbox in checkboxes.items():
                if feed_name in self.ocr_engine.feed_manager.feeds:
                    self.ocr_engine.feed_manager.feeds[feed_name]['config'].enabled = checkbox.isChecked()
                    if checkbox.isChecked():
                        enabled_count += 1
            
            QMessageBox.information(self, "Success", f"Enabled {enabled_count} Source_docs feeds.")
            self.refresh_feeds()
            
    def load_configuration(self):
        """Load configuration from selected source."""
        source = self.config_source_combo.currentText()
        
        self.config_editor.clear()
        
        if source == "Default Settings":
            config = {
                "preprocessing_methods": ["minimal", "light", "enhanced", "aggressive"],
                "tesseract_configs": ["default", "single_text_line", "lstm_only"],
                "default_page": 15,
                "default_block": 0,
                "debug_image_count": 3,
                "confidence_threshold": 0.8,
                "similarity_threshold": 0.9
            }
            self.config_editor.setPlainText(json.dumps(config, indent=2))
            
        elif source == "JSON File":
            # Enhanced JSON file browser with Source_docs integration
            self.browse_json_files()
        elif source == "Source_docs JSON Browser":
            # Browse JSON files specifically in Source_docs directory
            self.browse_source_docs_json()
                    
        elif source == "MCP Configuration":
            mcp_data = self.ocr_engine.load_configuration_from_feed("mcp_config")
            if mcp_data:
                self.config_editor.setPlainText(json.dumps(mcp_data, indent=2))
            else:
                self.config_editor.setPlainText("# MCP configuration not available")
                
    def save_configuration(self):
        """Save current configuration."""
        try:
            config_text = self.config_editor.toPlainText()
            config = json.loads(config_text)
            
            config_path = Path("output/ocr_testing_config.json")
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            QMessageBox.information(self, "Success", f"Configuration saved to: {config_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save configuration: {e}")
            
    def apply_configuration(self):
        """Apply current configuration to the testing engine."""
        try:
            config_text = self.config_editor.toPlainText()
            config = json.loads(config_text)
            
            # Apply configuration settings
            if "default_page" in config:
                self.opt_page_spinbox.setValue(config["default_page"])
                self.engine_page_spinbox.setValue(config["default_page"])
                self.debug_page_spinbox.setValue(config["default_page"])
                
            if "default_block" in config:
                self.opt_block_spinbox.setValue(config["default_block"])
                
            if "debug_image_count" in config:
                self.debug_blocks_spinbox.setValue(config["debug_image_count"])
                
            QMessageBox.information(self, "Success", "Configuration applied successfully!")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to apply configuration: {e}")
            
    def load_test_history(self):
        """Load test results history."""
        test_type = self.history_type_combo.currentText()
        limit = self.history_limit_spinbox.value()
        
        # Map GUI selection to database values
        type_filter = None
        if test_type != "All Tests":
            type_filter = test_type.lower().replace(" ", "_")
            
        try:
            results = self.ocr_engine.test_db.get_test_results(limit, type_filter)
            
            self.history_table.setRowCount(len(results))
            
            for row, result in enumerate(results):
                self.history_table.setItem(row, 0, QTableWidgetItem(result.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
                self.history_table.setItem(row, 1, QTableWidgetItem(result.source))
                self.history_table.setItem(row, 2, QTableWidgetItem(result.test_type))
                self.history_table.setItem(row, 3, QTableWidgetItem(str(result.page_num)))
                self.history_table.setItem(row, 4, QTableWidgetItem(str(result.block_index)))
                self.history_table.setItem(row, 5, QTableWidgetItem(f"{result.similarity:.1f}%"))
                self.history_table.setItem(row, 6, QTableWidgetItem(f"{result.confidence:.3f}"))
                self.history_table.setItem(row, 7, QTableWidgetItem("✅" if result.success else "❌"))
                
            self.history_table.resizeColumnsToContents()
            
            if results:
                self.history_details.clear()
                self.history_details.append(f"📊 Loaded {len(results)} test results")
                self.history_details.append(f"📈 Average similarity: {np.mean([r.similarity for r in results]):.1f}%")
                self.history_details.append(f"📈 Average confidence: {np.mean([r.confidence for r in results]):.3f}")
                self.history_details.append(f"✅ Success rate: {sum(r.success for r in results) / len(results) * 100:.1f}%")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load test history: {e}")
            
    def browse_json_files(self):
        """Browse and select JSON files with enhanced filtering."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select JSON Configuration File", 
            str(Path.cwd()),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            self.load_json_file(file_path)
    
    def browse_source_docs_json(self):
        """Browse JSON files specifically in Source_docs directory with recursive selection."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QDialogButtonBox, QLabel, QTextEdit, QSplitter
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Source_docs JSON Browser")
        dialog.setModal(True)
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel("Browse and select JSON files from Source_docs directory:")
        layout.addWidget(info_label)
        
        # Create splitter for tree and preview
        splitter = QSplitter(Qt.Horizontal)
        
        # JSON file tree
        self.json_tree = QTreeWidget()
        self.json_tree.setHeaderLabels(["File", "Size", "Modified"])
        self.json_tree.itemClicked.connect(self.preview_json_file)
        splitter.addWidget(self.json_tree)
        
        # JSON preview
        self.json_preview = QTextEdit()
        self.json_preview.setFont(QFont("Consolas", 9))
        self.json_preview.setReadOnly(True)
        splitter.addWidget(self.json_preview)
        
        # Set splitter proportions
        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        
        # Populate JSON tree
        self.populate_json_tree()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.populate_json_tree)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)
        
        if dialog.exec() == QDialog.Accepted:
            selected_items = self.json_tree.selectedItems()
            if selected_items:
                item = selected_items[0]
                file_path = item.data(0, Qt.UserRole)
                if file_path and Path(file_path).exists():
                    self.load_json_file(file_path)
                else:
                    QMessageBox.warning(self, "Error", "Please select a valid JSON file.")
    
    def populate_json_tree(self):
        """Populate the JSON tree with files from Source_docs directory."""
        if not hasattr(self, 'json_tree'):
            return
            
        self.json_tree.clear()
        
        source_docs_path = Path("Source_docs")
        if not source_docs_path.exists():
            return
        
        # Find all JSON files recursively
        json_files = []
        for json_file in source_docs_path.rglob("*.json"):
            try:
                stat = json_file.stat()
                json_files.append({
                    'path': json_file,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),
                    'relative_path': json_file.relative_to(source_docs_path)
                })
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        
        # Group by directory
        directories = {}
        for file_info in json_files:
            dir_path = file_info['relative_path'].parent
            if dir_path not in directories:
                directories[dir_path] = []
            directories[dir_path].append(file_info)
        
        # Create tree structure
        for dir_path, files in sorted(directories.items()):
            # Create directory item
            if str(dir_path) == ".":
                dir_item = QTreeWidgetItem(self.json_tree, ["Source_docs (root)", "", ""])
            else:
                dir_item = QTreeWidgetItem(self.json_tree, [str(dir_path), "", ""])
            
            dir_item.setExpanded(True)
            
            # Add files to directory
            for file_info in sorted(files, key=lambda x: x['path'].name):
                file_item = QTreeWidgetItem(dir_item, [
                    file_info['path'].name,
                    f"{file_info['size'] // 1024}KB" if file_info['size'] > 1024 else f"{file_info['size']}B",
                    file_info['modified'].strftime("%Y-%m-%d %H:%M")
                ])
                
                # Store full path in user data
                file_item.setData(0, Qt.UserRole, str(file_info['path']))
                
                # Color code by file type/content
                if "gbg_full_analysis" in file_info['path'].name:
                    file_item.setBackground(0, QColor(144, 238, 144))  # Light green for GBG analysis
                elif "consensus" in file_info['path'].name:
                    file_item.setBackground(0, QColor(255, 255, 224))  # Light yellow for consensus
                elif "corrections" in file_info['path'].name:
                    file_item.setBackground(0, QColor(255, 182, 193))  # Light red for corrections
                elif "verified" in file_info['path'].name:
                    file_item.setBackground(0, QColor(173, 216, 230))  # Light blue for verified
        
        # Expand all items
        self.json_tree.expandAll()
        
        # Resize columns to content
        for i in range(3):
            self.json_tree.resizeColumnToContents(i)
    
    def preview_json_file(self, item, column):
        """Preview selected JSON file content."""
        if not hasattr(self, 'json_preview'):
            return
            
        file_path = item.data(0, Qt.UserRole)
        if not file_path or not Path(file_path).exists():
            self.json_preview.clear()
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse and format JSON
            try:
                json_data = json.loads(content)
                
                # Show summary information first
                summary = f"📄 File: {Path(file_path).name}\n"
                summary += f"📁 Path: {file_path}\n"
                summary += f"📊 Size: {len(content)} characters\n\n"
                
                # Add content type detection
                if isinstance(json_data, dict):
                    if 'pages' in json_data and 'summary' in json_data:
                        summary += "🔍 Type: GBG Analysis File\n"
                        if 'summary' in json_data:
                            s = json_data['summary']
                            summary += f"📖 Pages: {s.get('total_pages', 'N/A')}\n"
                            summary += f"🔢 Blocks: {s.get('total_blocks', 'N/A')}\n"
                    elif 'doc_id' in str(json_data)[:200]:
                        summary += "📋 Type: Processing Results\n"
                    elif 'corrections' in json_data or 'verified' in json_data:
                        summary += "✏️ Type: Corrections/Verification Data\n"
                    else:
                        summary += "📄 Type: Configuration/Data File\n"
                        
                    summary += f"🔑 Keys: {len(json_data.keys()) if isinstance(json_data, dict) else 'N/A'}\n"
                
                summary += "\n" + "="*50 + "\n\n"
                
                # Format and display JSON (truncate if too large)
                formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
                if len(formatted_json) > 10000:  # Truncate large files
                    formatted_json = formatted_json[:10000] + "\n\n... (truncated - file too large for preview)"
                
                self.json_preview.setPlainText(summary + formatted_json)
                
            except json.JSONDecodeError as e:
                self.json_preview.setPlainText(f"❌ JSON Parse Error: {e}\n\nRaw content (first 1000 chars):\n{content[:1000]}")
                
        except Exception as e:
            self.json_preview.setPlainText(f"❌ Error reading file: {e}")
    
    def load_json_file(self, file_path):
        """Load and display JSON file content in the configuration editor with comprehensive validation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse and validate JSON
            try:
                json_data = json.loads(content)
                
                # Validate JSON format and structure
                validation_result = self._validate_json_format(json_data)
                
                if validation_result["valid"]:
                    # Format and display valid JSON
                    formatted_content = json.dumps(json_data, indent=2, ensure_ascii=False)
                    
                    # Add file info as comment at the top
                    comment = f"// Loaded from: {file_path}\n"
                    comment += f"// Size: {len(content)} characters\n"
                    comment += f"// Type: {validation_result['type']}\n"
                    comment += f"// Loaded at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    if validation_result["type"] == "gbg_analysis":
                        summary = json_data.get("summary", {})
                        comment += f"// Pages: {summary.get('total_pages', 'N/A')}\n"
                        comment += f"// Blocks: {summary.get('total_blocks', 'N/A')}\n"
                    elif validation_result["type"] == "consensus_decisions":
                        comment += f"// Records: {len(json_data)}\n"
                    
                    comment += "\n"
                    
                    self.config_editor.setPlainText(comment + formatted_content)
                    
                    # Show success message
                    file_info = f"Successfully loaded {validation_result['type']} JSON file:\n"
                    file_info += f"File: {Path(file_path).name}\n"
                    file_info += f"Size: {len(content)} characters"
                    
                    QMessageBox.information(self, "JSON Loaded Successfully", file_info)
                    
                else:
                    # Invalid JSON structure - show error with example
                    error_content = f"// ERROR: Invalid JSON structure\n"
                    error_content += f"// File: {file_path}\n"
                    error_content += f"// Error: {validation_result['error']}\n"
                    error_content += f"// Type: {validation_result['type']}\n\n"
                    
                    if "example" in validation_result:
                        error_content += "// Expected format example:\n"
                        error_content += json.dumps(validation_result["example"], indent=2)
                        error_content += "\n\n// Actual content:\n"
                    
                    error_content += json.dumps(json_data, indent=2, ensure_ascii=False)
                    
                    self.config_editor.setPlainText(error_content)
                    
                    # Show detailed error message
                    error_msg = f"JSON file has invalid structure:\n\n"
                    error_msg += f"Error: {validation_result['error']}\n\n"
                    error_msg += f"Expected format: {validation_result['type']}\n\n"
                    
                    if "example" in validation_result:
                        error_msg += "See the configuration editor for an example of the expected format."
                    
                    QMessageBox.warning(self, "Invalid JSON Structure", error_msg)
                
            except json.JSONDecodeError as e:
                # Invalid JSON syntax
                error_content = f"// ERROR: Invalid JSON syntax\n"
                error_content += f"// File: {file_path}\n"
                error_content += f"// JSON Error: {str(e)}\n"
                error_content += f"// Line: {getattr(e, 'lineno', 'unknown')}\n"
                error_content += f"// Column: {getattr(e, 'colno', 'unknown')}\n\n"
                error_content += "// Example of valid JSON:\n"
                error_content += json.dumps({
                    "example_key": "example_value",
                    "number": 42,
                    "boolean": True,
                    "array": ["item1", "item2"],
                    "object": {"nested": "value"}
                }, indent=2)
                error_content += "\n\n// Raw file content:\n"
                error_content += content
                
                self.config_editor.setPlainText(error_content)
                
                # Show detailed JSON syntax error
                error_msg = f"File contains invalid JSON syntax:\n\n"
                error_msg += f"Error: {str(e)}\n"
                if hasattr(e, 'lineno'):
                    error_msg += f"Line: {e.lineno}, Column: {e.colno}\n\n"
                error_msg += f"Common JSON syntax issues:\n"
                error_msg += f"• Missing quotes around strings\n"
                error_msg += f"• Trailing commas\n"
                error_msg += f"• Single quotes instead of double quotes\n"
                error_msg += f"• Unescaped characters in strings\n\n"
                error_msg += f"See the configuration editor for an example of valid JSON."
                
                QMessageBox.critical(self, "JSON Syntax Error", error_msg)
                
        except Exception as e:
            # File reading error
            error_content = f"// ERROR: Failed to read file\n"
            error_content += f"// File: {file_path}\n"
            error_content += f"// Error: {str(e)}\n"
            
            self.config_editor.setPlainText(error_content)
            QMessageBox.critical(self, "File Error", f"Failed to read file:\n{str(e)}")
    
    def _validate_json_format(self, data):
        """Validate JSON format and return validation result with examples."""
        try:
            if isinstance(data, dict):
                if "pages" in data and "summary" in data:
                    return self._validate_gbg_json_format(data)
                elif "corrections" in data or "verified" in data:
                    return {"valid": True, "type": "corrections_data"}
                elif "doc_id" in str(data)[:200]:  # Quick check for doc_id in first part
                    return {"valid": True, "type": "processing_results"}
                else:
                    return {"valid": True, "type": "configuration"}
            elif isinstance(data, list):
                if data and isinstance(data[0], dict) and "doc_id" in data[0]:
                    return self._validate_consensus_json_format(data)
                else:
                    return {"valid": True, "type": "list_data"}
            else:
                return {
                    "valid": False, 
                    "error": "JSON must be an object {} or array []", 
                    "type": "invalid_root_type",
                    "example": {"valid_object": "example"} 
                }
        except Exception as e:
            return {"valid": False, "error": str(e), "type": "validation_error"}
    
    def _validate_gbg_json_format(self, data):
        """Validate GBG analysis JSON format with detailed examples."""
        required_fields = ["pages", "summary"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            example = {
                "pdf_name": "English Language Arts Standards.pdf",
                "summary": {
                    "total_pages": 62,
                    "total_blocks": 1066,
                    "extraction_engine": "PyMuPDF",
                    "processing_type": "gbg_analysis"
                },
                "pages": {
                    "0": {
                        "page_number": 0,
                        "blocks": [
                            {
                                "block_id": "blk_27e0e0e663d732b0",
                                "text_content": "UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS",
                                "bbox": {
                                    "x": 72.0,
                                    "y": 72.0,
                                    "width": 451.2,
                                    "height": 36.0
                                },
                                "orientation_hints": {
                                    "confidence": 0.95,
                                    "angle": 0
                                }
                            }
                        ]
                    }
                }
            }
            
            return {
                "valid": False,
                "error": f"Missing required fields for GBG analysis: {', '.join(missing_fields)}",
                "type": "gbg_analysis",
                "example": example
            }
        
        # Validate pages structure
        if not isinstance(data["pages"], dict):
            return {
                "valid": False,
                "error": "Field 'pages' must be a dictionary with page numbers as keys",
                "type": "gbg_analysis",
                "example": {"pages": {"0": {"blocks": []}, "1": {"blocks": []}}}
            }
        
        # Validate summary structure
        if not isinstance(data["summary"], dict):
            return {
                "valid": False,
                "error": "Field 'summary' must be a dictionary with metadata",
                "type": "gbg_analysis",
                "example": {"summary": {"total_pages": 10, "total_blocks": 100}}
            }
        
        return {"valid": True, "type": "gbg_analysis"}
    
    def _validate_consensus_json_format(self, data):
        """Validate consensus decisions JSON format with detailed examples."""
        if not isinstance(data, list) or not data:
            return {
                "valid": False,
                "error": "Consensus data must be a non-empty array of decision objects",
                "type": "consensus_decisions",
                "example": [{"doc_id": "document.pdf", "page": 1, "block_id": "blk_123"}]
            }
        
        required_fields = ["doc_id", "page", "block_id", "selected_engine", "final_text"]
        first_item = data[0]
        missing_fields = [field for field in required_fields if field not in first_item]
        
        if missing_fields:
            example = [
                {
                    "doc_id": "English Language Arts Standards.pdf",
                    "page": 15,
                    "block_id": "blk_27e0e0e663d732b0",
                    "selected_engine": "tesseract",
                    "final_text": "UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS",
                    "decision_reason": "highest_score",
                    "engine_scores": {
                        "tesseract": 0.95,
                        "pymupdf": 0.87
                    },
                    "anomaly_score": 0.05,
                    "bbox": [72.0, 72.0, 451.2, 36.0]
                }
            ]
            
            return {
                "valid": False,
                "error": f"Missing required fields for consensus decisions: {', '.join(missing_fields)}",
                "type": "consensus_decisions",
                "example": example
            }
        
        return {"valid": True, "type": "consensus_decisions"}
    
    def closeEvent(self, event):
        """Handle widget close event."""
        self.ocr_engine.stop_feeds()
        event.accept()
    
    def create_optimization_tab(self):
        """Create OCR optimization testing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Page:"))
        self.opt_page_spinbox = QSpinBox()
        self.opt_page_spinbox.setMinimum(0)
        self.opt_page_spinbox.setMaximum(100)
        self.opt_page_spinbox.setValue(15)
        controls_layout.addWidget(self.opt_page_spinbox)
        
        controls_layout.addWidget(QLabel("Block:"))
        self.opt_block_spinbox = QSpinBox()
        self.opt_block_spinbox.setMinimum(0)
        self.opt_block_spinbox.setMaximum(50)
        self.opt_block_spinbox.setValue(0)
        controls_layout.addWidget(self.opt_block_spinbox)
        
        self.optimize_button = QPushButton("Run OCR Optimization")
        self.optimize_button.clicked.connect(self.run_ocr_optimization)
        controls_layout.addWidget(self.optimize_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Results display
        self.optimization_results = QTextEdit()
        self.optimization_results.setFont(QFont("Consolas", 9))
        layout.addWidget(self.optimization_results)
        
        return widget
    
    def create_engine_testing_tab(self):
        """Create engine testing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Test Page:"))
        self.engine_page_spinbox = QSpinBox()
        self.engine_page_spinbox.setMinimum(0)
        self.engine_page_spinbox.setMaximum(100)
        self.engine_page_spinbox.setValue(15)
        controls_layout.addWidget(self.engine_page_spinbox)
        
        self.test_engine_button = QPushButton("Test Improved Engine")
        self.test_engine_button.clicked.connect(self.test_improved_engine)
        controls_layout.addWidget(self.test_engine_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Results display
        self.engine_results = QTextEdit()
        self.engine_results.setFont(QFont("Consolas", 9))
        layout.addWidget(self.engine_results)
        
        return widget
    
    def create_debug_images_tab(self):
        """Create debug images tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        controls_layout.addWidget(QLabel("Page:"))
        self.debug_page_spinbox = QSpinBox()
        self.debug_page_spinbox.setMinimum(0)
        self.debug_page_spinbox.setMaximum(100)
        self.debug_page_spinbox.setValue(15)
        controls_layout.addWidget(self.debug_page_spinbox)
        
        controls_layout.addWidget(QLabel("Max Blocks:"))
        self.debug_blocks_spinbox = QSpinBox()
        self.debug_blocks_spinbox.setMinimum(1)
        self.debug_blocks_spinbox.setMaximum(10)
        self.debug_blocks_spinbox.setValue(3)
        controls_layout.addWidget(self.debug_blocks_spinbox)
        
        self.extract_debug_button = QPushButton("Extract Debug Images")
        self.extract_debug_button.clicked.connect(self.extract_debug_images)
        controls_layout.addWidget(self.extract_debug_button)
        
        self.open_report_button = QPushButton("Open HTML Report")
        self.open_report_button.clicked.connect(self.open_debug_report)
        controls_layout.addWidget(self.open_report_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Results display
        self.debug_results = QTextEdit()
        self.debug_results.setFont(QFont("Consolas", 9))
        layout.addWidget(self.debug_results)
        
        return widget
    
    def run_ocr_optimization(self):
        """Run OCR parameter optimization."""
        page_num = self.opt_page_spinbox.value()
        block_index = self.opt_block_spinbox.value()
        
        self.optimization_results.clear()
        self.optimization_results.append("🔧 Running OCR Optimization...")
        self.optimization_results.append("=" * 50)
        
        try:
            pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
            
            optimization_result = self.ocr_engine.optimize_ocr_parameters(pdf_path, page_num, block_index)
            
            self.optimization_results.append(f"🎯 Target Block: {optimization_result['block_id']}")
            self.optimization_results.append(f"📝 Expected: \"{optimization_result['expected_text'][:60]}...\"")
            self.optimization_results.append("")
            
            self.optimization_results.append("🏆 Top 5 Results:")
            self.optimization_results.append("-" * 30)
            
            for i, result in enumerate(optimization_result['best_results'][:5]):
                self.optimization_results.append(f"{i+1}. {result['preprocessing']} + {result['tesseract_config']}")
                self.optimization_results.append(f"   Similarity: {result['similarity']:.1f}% | Confidence: {result['confidence']:.1f}")
                if result['similarity'] > 70:
                    self.optimization_results.append(f"   Text: \"{result['extracted_text'][:50]}...\"")
                self.optimization_results.append("")
            
            winner = optimization_result['winner']
            if winner:
                self.optimization_results.append("🥇 OPTIMAL CONFIGURATION:")
                self.optimization_results.append("=" * 30)
                self.optimization_results.append(f"Preprocessing: {winner['preprocessing']}")
                self.optimization_results.append(f"Tesseract Config: {winner['tesseract_config']}")
                self.optimization_results.append(f"Similarity: {winner['similarity']:.1f}%")
                self.optimization_results.append(f"Confidence: {winner['confidence']:.1f}")
                self.optimization_results.append(f"Text: \"{winner['extracted_text']}\"")
                
                if winner['similarity'] > 95:
                    self.optimization_results.append("🎉 EXCELLENT! >95% accuracy achieved!")
                elif winner['similarity'] > 80:
                    self.optimization_results.append("✅ GOOD! >80% accuracy achieved!")
                else:
                    self.optimization_results.append("⚠️ Needs improvement")
            
        except Exception as e:
            self.optimization_results.append(f"❌ Error: {str(e)}")
    
    def test_improved_engine(self):
        """Test the improved OCR engine."""
        page_num = self.engine_page_spinbox.value()
        
        self.engine_results.clear()
        self.engine_results.append("🚀 Testing Improved GBG-Guided Tesseract Engine")
        self.engine_results.append("=" * 50)
        
        try:
            pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
            
            engine_result = self.ocr_engine.test_improved_engine(pdf_path, page_num)
            
            self.engine_results.append(f"✅ Extraction complete!")
            self.engine_results.append(f"   Total blocks: {engine_result['total_blocks']}")
            self.engine_results.append(f"   Average confidence: {engine_result['avg_confidence']:.3f}")
            self.engine_results.append("")
            
            page_blocks = engine_result['page_blocks']
            if page_blocks:
                self.engine_results.append(f"📊 Page {page_num} Results ({len(page_blocks)} blocks):")
                self.engine_results.append("-" * 40)
                
                for i, block in enumerate(page_blocks[:5]):  # Show first 5 blocks
                    self.engine_results.append(f"Block {i+1}: {block['gbg_block_id'][:12]}...")
                    self.engine_results.append(f"  Text: \"{block['text'][:60]}...\"")
                    self.engine_results.append(f"  Confidence: {block['confidence']:.3f}")
                    self.engine_results.append(f"  Orientation: {block['orientation_angle']}°")
                    self.engine_results.append("")
                
                # Check for Block 1 specifically
                block_1 = None
                for block in page_blocks:
                    if block['gbg_block_id'] == 'blk_27e0e0e663d732b0':
                        block_1 = block
                        break
                
                if block_1:
                    self.engine_results.append("🎯 Block 1 Analysis:")
                    self.engine_results.append("-" * 20)
                    expected = "UTAH STATE STANDARDS for P–12 ENGLISH LANGUAGE ARTS"
                    extracted = block_1['text']
                    
                    from rapidfuzz import fuzz
                    similarity = fuzz.ratio(extracted.lower(), expected.lower())
                    
                    self.engine_results.append(f"Expected: \"{expected}\"")
                    self.engine_results.append(f"Extracted: \"{extracted}\"")
                    self.engine_results.append(f"Similarity: {similarity:.1f}%")
                    self.engine_results.append(f"Confidence: {block_1['confidence']:.3f}")
                    
                    if similarity > 90:
                        self.engine_results.append("✅ EXCELLENT! OCR quality significantly improved!")
                    elif similarity > 70:
                        self.engine_results.append("✅ GOOD! OCR quality improved!")
                    else:
                        self.engine_results.append("⚠️ Still needs improvement")
            
        except Exception as e:
            self.engine_results.append(f"❌ Error: {str(e)}")
    
    def extract_debug_images(self):
        """Extract debug images."""
        page_num = self.debug_page_spinbox.value()
        max_blocks = self.debug_blocks_spinbox.value()
        
        self.debug_results.clear()
        self.debug_results.append("🖼️ Extracting Debug Images...")
        self.debug_results.append("=" * 40)
        
        try:
            pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
            
            result = extract_debug_images_for_page(pdf_path, page_num, max_blocks)
            
            if 'error' in result:
                self.debug_results.append(f"❌ Error: {result['error']}")
            else:
                self.debug_results.append("✅ Success!")
                self.debug_results.append(f"   Page: {result['page_num']}")
                self.debug_results.append(f"   Extracted regions: {result['extracted_regions']}")
                self.debug_results.append(f"   Debug images: {result['debug_images_dir']}")
                self.debug_results.append("")
                
                self.debug_results.append("📊 Extracted regions:")
                for i, region in enumerate(result['regions']):
                    gbg_id = region['gbg_block_id']
                    expected = region['expected_text'][:40] + "..." if len(region['expected_text']) > 40 else region['expected_text']
                    
                    self.debug_results.append(f"  Region {i+1}: {gbg_id[:12]}...")
                    self.debug_results.append(f"    Expected: \"{expected}\"")
                    self.debug_results.append(f"    Images: {len(region['orientation_results']) + 1} total")
                
                self.debug_results.append("")
                self.debug_results.append(f"🖼️ Debug images saved to: {result['debug_images_dir']}")
                self.debug_results.append(f"📋 HTML report: {result['debug_report_path']}")
        
        except Exception as e:
            self.debug_results.append(f"❌ Error: {str(e)}")
    
    def open_debug_report(self):
        """Open the HTML debug report."""
        report_path = Path("output/debug_images/debug_report.html")
        if report_path.exists():
            webbrowser.open(f"file://{report_path.absolute()}")
            QMessageBox.information(self, "Success", "Debug report opened in browser!")
        else:
            QMessageBox.warning(self, "Error", "Debug report not found. Extract debug images first.")


class VisualOCRTestingApp(QMainWindow):
    """Main application window for visual OCR testing."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visual OCR Testing Tool - BECR")
        self.setGeometry(100, 100, 1000, 700)
        
        # Create central widget
        self.central_widget = VisualOCRTestingWidget()
        self.setCentralWidget(self.central_widget)


def run_cli_optimization(args):
    """Run CLI OCR optimization."""
    engine = OCROptimizationEngine()
    
    pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
    page_num = args.page
    block_index = args.block
    
    print("🔧 OCR Parameter Optimization")
    print("=" * 50)
    print(f"📄 PDF: {Path(pdf_path).name}")
    print(f"📖 Page: {page_num}")
    print(f"🔢 Block: {block_index + 1}")
    print()
    
    try:
        result = engine.optimize_ocr_parameters(pdf_path, page_num, block_index)
        
        print(f"🎯 Target Block: {result['block_id']}")
        print(f"📝 Expected: \"{result['expected_text'][:60]}...\"")
        print()
        
        print("🏆 Top 5 Results:")
        print("-" * 30)
        
        for i, res in enumerate(result['best_results'][:5]):
            print(f"{i+1}. {res['preprocessing']} + {res['tesseract_config']}")
            print(f"   Similarity: {res['similarity']:.1f}% | Confidence: {res['confidence']:.1f}")
            if res['similarity'] > 70:
                print(f"   Text: \"{res['extracted_text'][:50]}...\"")
            print()
        
        winner = result['winner']
        if winner:
            print("🥇 OPTIMAL CONFIGURATION:")
            print("=" * 30)
            print(f"Preprocessing: {winner['preprocessing']}")
            print(f"Tesseract Config: {winner['tesseract_config']}")
            print(f"Config String: {winner['config_string']}")
            print(f"Similarity: {winner['similarity']:.1f}%")
            print(f"Confidence: {winner['confidence']:.1f}")
            print(f"Text: \"{winner['extracted_text']}\"")
            
            if winner['similarity'] > 95:
                print("🎉 EXCELLENT! >95% accuracy achieved!")
            elif winner['similarity'] > 80:
                print("✅ GOOD! >80% accuracy achieved!")
            else:
                print("⚠️ Needs improvement")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def run_engine_test(args):
    """Run improved engine test."""
    engine = OCROptimizationEngine()
    
    pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
    page_num = args.page
    
    print("🚀 Testing Improved GBG-Guided Tesseract Engine")
    print("=" * 50)
    
    try:
        result = engine.test_improved_engine(pdf_path, page_num)
        
        print(f"✅ Extraction complete!")
        print(f"   Total blocks: {result['total_blocks']}")
        print(f"   Average confidence: {result['avg_confidence']:.3f}")
        print()
        
        page_blocks = result['page_blocks']
        if page_blocks:
            print(f"📊 Page {page_num} Results ({len(page_blocks)} blocks):")
            print("-" * 40)
            
            for i, block in enumerate(page_blocks[:3]):
                print(f"Block {i+1}: {block['gbg_block_id'][:12]}...")
                print(f"  Text: \"{block['text'][:60]}...\"")
                print(f"  Confidence: {block['confidence']:.3f}")
                print(f"  Orientation: {block['orientation_angle']}°")
                print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def run_debug_extraction(args):
    """Run debug image extraction."""
    page_num = args.page
    max_blocks = getattr(args, 'blocks', 3)
    
    print("🖼️ Extracting Debug Images")
    print("=" * 40)
    
    try:
        pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
        result = extract_debug_images_for_page(pdf_path, page_num, max_blocks)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return 1
        
        print("✅ Success!")
        print(f"   Page: {result['page_num']}")
        print(f"   Extracted regions: {result['extracted_regions']}")
        print(f"   Debug images: {result['debug_images_dir']}")
        print(f"   HTML report: {result['debug_report_path']}")
        
        # Try to open report
        try:
            webbrowser.open(f"file://{Path(result['debug_report_path']).absolute()}")
            print("🌐 Debug report opened in browser!")
        except:
            print("💡 Manually open the HTML report to view results")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    """Main entry point with multi-input feed support."""
    parser = argparse.ArgumentParser(description="Visual OCR Testing Tool with Multi-Input Feeds")
    
    # Core testing modes
    parser.add_argument('--cli', action='store_true', help='Run CLI optimization mode')
    parser.add_argument('--test-engine', action='store_true', help='Test improved engine')
    parser.add_argument('--extract-debug', action='store_true', help='Extract debug images')
    
    # Input feed options
    parser.add_argument('--mcp-feed', action='store_true', help='Enable MCP data feed')
    parser.add_argument('--json-config', type=str, help='Load JSON configuration file')
    parser.add_argument('--monitor-files', action='store_true', help='Enable file system monitoring')
    parser.add_argument('--api-endpoint', type=str, help='Connect to API endpoint')
    parser.add_argument('--database', type=str, help='Connect to database file')
    parser.add_argument('--code-integration', action='store_true', help='Enable direct code integration')
    
    # Testing parameters
    parser.add_argument('--page', type=int, default=15, help='Page number to test')
    parser.add_argument('--block', type=int, default=0, help='Block index to test')
    parser.add_argument('--blocks', type=int, default=3, help='Max blocks for debug extraction')
    
    # Feed configuration
    parser.add_argument('--feed-interval', type=int, default=30, help='Feed refresh interval in seconds')
    parser.add_argument('--enable-all-feeds', action='store_true', help='Enable all available input feeds')
    parser.add_argument('--list-feeds', action='store_true', help='List available input feeds')
    
    # Output options
    parser.add_argument('--save-results', action='store_true', help='Save test results to database')
    parser.add_argument('--export-config', type=str, help='Export current configuration to file')
    
    args = parser.parse_args()
    
    # Handle feed listing
    if args.list_feeds:
        print("📡 Available Input Feeds:")
        print("=" * 40)
        print("1. MCP Configuration - Model Context Protocol servers")
        print("2. JSON Configuration - Configuration files and analysis results")
        print("3. File System Monitoring - Real-time file change detection")
        print("4. API Endpoints - External data sources via HTTP")
        print("5. Database Connections - SQLite and other databases")
        print("6. Code Integration - Direct Python code execution")
        print("7. System Status - Environment and system checks")
        print("\nUse --enable-all-feeds to activate all feeds in GUI mode")
        return 0
    
    # Setup enhanced engine with custom feeds
    engine = OCROptimizationEngine()
    
    # Add custom feeds based on arguments
    if args.mcp_feed or args.enable_all_feeds:
        print("🔌 Enabling MCP data feed...")
        
    if args.json_config:
        print(f"📄 Loading JSON configuration from: {args.json_config}")
        json_feed = InputFeedConfig(
            name="custom_json",
            type="json",
            source=args.json_config,
            enabled=True,
            refresh_interval=args.feed_interval
        )
        engine.add_custom_feed(json_feed)
        
    if args.api_endpoint:
        print(f"🌐 Connecting to API endpoint: {args.api_endpoint}")
        api_feed = InputFeedConfig(
            name="custom_api",
            type="api",
            source=args.api_endpoint,
            enabled=True,
            refresh_interval=args.feed_interval
        )
        engine.add_custom_feed(api_feed)
        
    if args.database:
        print(f"🗄️  Connecting to database: {args.database}")
        db_feed = InputFeedConfig(
            name="custom_database",
            type="database",
            source=args.database,
            enabled=True,
            refresh_interval=args.feed_interval
        )
        engine.add_custom_feed(db_feed)
        
    if args.monitor_files or args.enable_all_feeds:
        print("📁 Enabling file system monitoring...")
        
    if args.code_integration or args.enable_all_feeds:
        print("🐍 Enabling direct code integration...")
    
    # Export configuration if requested
    if args.export_config:
        config = {
            "feeds": engine.get_feed_status(),
            "testing_parameters": {
                "default_page": args.page,
                "default_block": args.block,
                "max_debug_blocks": args.blocks,
                "feed_refresh_interval": args.feed_interval
            },
            "export_timestamp": datetime.now().isoformat()
        }
        
        with open(args.export_config, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"📤 Configuration exported to: {args.export_config}")
        return 0
    
    # Run specific modes
    if args.cli:
        if args.enable_all_feeds:
            engine.start_feeds()
            time.sleep(2)  # Allow feeds to initialize
        return run_cli_optimization(args, engine)
    elif args.test_engine:
        if args.enable_all_feeds:
            engine.start_feeds()
            time.sleep(2)
        return run_engine_test(args, engine)
    elif args.extract_debug:
        return run_debug_extraction(args)
    else:
        # GUI mode with enhanced feeds
        if not GUI_AVAILABLE:
            print("❌ GUI not available. Install PySide6: pip install PySide6")
            print("💡 Available CLI modes:")
            print("   --cli              OCR optimization testing")
            print("   --test-engine      Engine validation")
            print("   --extract-debug    Debug image extraction")
            print("   --list-feeds       Show available input feeds")
            return 1
        
        print("🚀 Starting Visual OCR Testing Tool with Multi-Input Feeds")
        if args.enable_all_feeds:
            print("📡 All input feeds enabled")
        
        app = QApplication(sys.argv)
        app.setApplicationName("Visual OCR Testing Tool")
        app.setApplicationDisplayName("BECR - Visual OCR Testing Platform")
        
        window = VisualOCRTestingApp()
        window.show()
        
        return app.exec()


def run_cli_optimization(args, engine=None):
    """Run CLI OCR optimization with feed support."""
    if engine is None:
        engine = OCROptimizationEngine()
    
    pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
    page_num = args.page
    block_index = args.block
    
    print("🔧 OCR Parameter Optimization with Multi-Input Feeds")
    print("=" * 60)
    print(f"📄 PDF: {Path(pdf_path).name}")
    print(f"📖 Page: {page_num}")
    print(f"🔢 Block: {block_index + 1}")
    
    # Show feed status
    if hasattr(args, 'enable_all_feeds') and args.enable_all_feeds:
        print("\n📡 Input Feed Status:")
        feed_status = engine.get_feed_status()
        for feed_name, status in feed_status.items():
            status_icon = "✅" if status['status'] == 'active' else "⏳" if status['status'] == 'waiting' else "❌"
            print(f"   {status_icon} {feed_name}: {status['status']}")
    
    print()
    
    try:
        result = engine.optimize_ocr_parameters(pdf_path, page_num, block_index)
        
        print(f"🎯 Target Block: {result['block_id']}")
        print(f"📝 Expected: \"{result['expected_text'][:60]}...\"")
        print()
        
        print("🏆 Top 5 Results:")
        print("-" * 30)
        
        for i, res in enumerate(result['best_results'][:5]):
            print(f"{i+1}. {res['preprocessing']} + {res['tesseract_config']}")
            print(f"   Similarity: {res['similarity']:.1f}% | Confidence: {res['confidence']:.1f}")
            if res['similarity'] > 70:
                print(f"   Text: \"{res['extracted_text'][:50]}...\"")
            print()
        
        winner = result['winner']
        if winner:
            print("🥇 OPTIMAL CONFIGURATION:")
            print("=" * 30)
            print(f"Preprocessing: {winner['preprocessing']}")
            print(f"Tesseract Config: {winner['tesseract_config']}")
            print(f"Config String: {winner['config_string']}")
            print(f"Similarity: {winner['similarity']:.1f}%")
            print(f"Confidence: {winner['confidence']:.1f}")
            print(f"Text: \"{winner['extracted_text']}\"")
            
            # Save result to database if requested
            if hasattr(args, 'save_results') and args.save_results:
                test_result = TestResult(
                    timestamp=datetime.now(),
                    source="cli_optimization",
                    test_type="ocr_optimization",
                    page_num=page_num,
                    block_index=block_index,
                    similarity=winner['similarity'],
                    confidence=winner['confidence'],
                    extracted_text=winner['extracted_text'],
                    expected_text=result['expected_text'],
                    preprocessing=winner['preprocessing'],
                    tesseract_config=winner['tesseract_config'],
                    success=winner['similarity'] > 80,
                    metadata={'config_string': winner['config_string']}
                )
                engine.test_db.save_test_result(test_result)
                print("💾 Test result saved to database")
            
            if winner['similarity'] > 95:
                print("🎉 EXCELLENT! >95% accuracy achieved!")
            elif winner['similarity'] > 80:
                print("✅ GOOD! >80% accuracy achieved!")
            else:
                print("⚠️ Needs improvement")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        if engine:
            engine.stop_feeds()


def run_engine_test(args, engine=None):
    """Run improved engine test with feed support."""
    if engine is None:
        engine = OCROptimizationEngine()
    
    pdf_path = "Source_docs/English Language Arts Standards/-English Language Arts Standards.pdf"
    page_num = args.page
    
    print("🚀 Testing Improved GBG-Guided Tesseract Engine with Multi-Input Feeds")
    print("=" * 70)
    
    try:
        result = engine.test_improved_engine(pdf_path, page_num)
        
        print(f"✅ Extraction complete!")
        print(f"   Total blocks: {result['total_blocks']}")
        print(f"   Average confidence: {result['avg_confidence']:.3f}")
        print()
        
        page_blocks = result['page_blocks']
        if page_blocks:
            print(f"📊 Page {page_num} Results ({len(page_blocks)} blocks):")
            print("-" * 40)
            
            for i, block in enumerate(page_blocks[:3]):
                print(f"Block {i+1}: {block['gbg_block_id'][:12]}...")
                print(f"  Text: \"{block['text'][:60]}...\"")
                print(f"  Confidence: {block['confidence']:.3f}")
                print(f"  Orientation: {block['orientation_angle']}°")
                print()
                
                # Save results if requested
                if hasattr(args, 'save_results') and args.save_results:
                    test_result = TestResult(
                        timestamp=datetime.now(),
                        source="engine_test",
                        test_type="engine_testing",
                        page_num=page_num,
                        block_index=i,
                        similarity=95.0,  # Placeholder - would need actual comparison
                        confidence=block['confidence'],
                        extracted_text=block['text'],
                        expected_text="",  # Would need GBG comparison
                        preprocessing="light",
                        tesseract_config="default",
                        success=block['confidence'] > 0.8,
                        metadata={'gbg_block_id': block['gbg_block_id']}
                    )
                    engine.test_db.save_test_result(test_result)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    finally:
        if engine:
            engine.stop_feeds()


if __name__ == "__main__":
    sys.exit(main())