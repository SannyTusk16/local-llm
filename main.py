#!/usr/bin/env python3
"""
ForumLLM - Entry Point
A nostalgic local LLM chat client.

Usage:
    python main.py
    
Or run as module:
    python -m src.main
"""

import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import PyQt6
    except ImportError:
        missing.append("PyQt6")
    
    try:
        import markdown
    except ImportError:
        missing.append("markdown")
    
    try:
        import pygments
    except ImportError:
        missing.append("pygments")
    
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall them with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def check_ollama():
    """Check if Ollama is installed (warning only)."""
    from src.core.ollama_runner import OllamaRunner
    
    if not OllamaRunner.is_ollama_installed():
        print("Warning: Ollama is not installed or not running.")
        print("Install from: https://ollama.ai")
        print("Some features will be unavailable.\n")


def main():
    """Main entry point."""
    # Check dependencies first
    check_dependencies()
    
    # Check Ollama
    check_ollama()
    
    # Import Qt components (after dependency check)
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    
    # Enable high DPI scaling BEFORE creating QApplication
    try:
        from PyQt6.QtCore import Qt
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass  # Not available in older PyQt6 versions
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("ForumLLM")
    app.setApplicationDisplayName("ForumLLM")
    app.setOrganizationName("ForumLLM")
    
    # Set application-wide font (cross-platform)
    font = QFont()
    font.setFamilies(["Segoe UI", "SF Pro Display", "Helvetica Neue", "Ubuntu", "sans-serif"])
    font.setPointSize(10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Import and create main window
    from src.app import ForumLLMApp
    
    window = ForumLLMApp()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
