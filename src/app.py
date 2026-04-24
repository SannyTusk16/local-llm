"""
ForumLLM - Main Application Window
Orchestrates all widgets and handles the main application logic.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QStatusBar, QLabel, QMessageBox,
    QMenuBar, QMenu, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QMetaObject, Q_ARG
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from pathlib import Path
from typing import Optional

from .widgets.sidebar import Sidebar
from .widgets.chat_panel import ChatPanel
from .widgets.input_area import InputArea
from .widgets.settings_dialog import SettingsDialog
from .core.config import Config
from .core.ollama_runner import OllamaRunner
from .core.chat_history import ChatHistory, Conversation


class ForumLLMApp(QMainWindow):
    """
    Main application window for ForumLLM.
    """
    
    # Signals for thread-safe callbacks
    _generation_complete = pyqtSignal()
    _generation_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.config = Config()
        self.chat_history = ChatHistory(self.config.get_data_dir() / "chat_history.db")
        self.ollama = OllamaRunner()
        
        # State
        self._current_conversation: Optional[Conversation] = None
        self._is_generating = False
        
        # Setup UI
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_statusbar()
        self._connect_signals()
        self._load_stylesheet()
        
        # Restore window state
        self._restore_window_state()
    
    def _setup_window(self) -> None:
        """Configure main window properties."""
        self.setWindowTitle("ForumLLM - Local LLM Chat")
        self.setMinimumSize(900, 600)
    
    def _setup_menu(self) -> None:
        """Setup application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_chat_action = QAction("&New Chat", self)
        new_chat_action.setShortcut(QKeySequence("Ctrl+N"))
        new_chat_action.triggered.connect(self._on_new_chat)
        file_menu.addAction(new_chat_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        copy_last_action = QAction("Copy Last &Response", self)
        copy_last_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_last_action.triggered.connect(self._copy_last_response)
        edit_menu.addAction(copy_last_action)
        
        edit_menu.addSeparator()
        
        clear_chat_action = QAction("&Clear Chat", self)
        clear_chat_action.triggered.connect(self._clear_current_chat)
        edit_menu.addAction(clear_chat_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        self.toggle_sidebar_action = QAction("Toggle &Sidebar", self)
        self.toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(self.toggle_sidebar_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_ui(self) -> None:
        """Setup main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Splitter for sidebar and main content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar
        self.sidebar = Sidebar(self.chat_history)
        self.splitter.addWidget(self.sidebar)
        
        # Main content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)
        
        # Chat panel
        self.chat_panel = ChatPanel()
        content_layout.addWidget(self.chat_panel, stretch=1)
        
        # Input area
        self.input_area = InputArea()
        content_layout.addWidget(self.input_area)
        
        self.splitter.addWidget(content_widget)
        
        # Set splitter sizes
        self.splitter.setSizes([280, 700])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.splitter)
    
    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Focus input
        focus_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_shortcut.activated.connect(self.input_area.focus_input)
    
    def _setup_statusbar(self) -> None:
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Model indicator
        self.model_label = QLabel("No model selected")
        self.statusbar.addWidget(self.model_label)
        
        # Spacer
        self.statusbar.addWidget(QLabel(""), stretch=1)
        
        # Status indicator
        self.status_label = QLabel("Ready")
        self.statusbar.addPermanentWidget(self.status_label)
    
    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Sidebar signals
        self.sidebar.model_selected.connect(self._on_model_selected)
        self.sidebar.new_chat_requested.connect(self._on_new_chat)
        self.sidebar.conversation_selected.connect(self._on_conversation_selected)
        self.sidebar.conversation_deleted.connect(self._on_conversation_deleted)
        self.sidebar.settings_requested.connect(self._show_settings)
        
        # Input area signals
        self.input_area.message_sent.connect(self._on_message_sent)        
        # Thread-safe callback signals
        self._generation_complete.connect(self._handle_generation_complete)
        self._generation_error.connect(self._handle_generation_error)    
    def _load_stylesheet(self) -> None:
        """Load and apply the QSS stylesheet."""
        # Try loading from file
        style_path = Path(__file__).parent.parent / "assets" / "styles" / "forum.qss"
        
        if style_path.exists():
            with open(style_path, 'r') as f:
                self.setStyleSheet(f.read())
        else:
            # Fallback: try relative to working directory
            alt_path = Path("assets/styles/forum.qss")
            if alt_path.exists():
                with open(alt_path, 'r') as f:
                    self.setStyleSheet(f.read())
    
    def _restore_window_state(self) -> None:
        """Restore window size and position."""
        ui = self.config.ui
        self.resize(ui.window_width, ui.window_height)
        
        if ui.window_x is not None and ui.window_y is not None:
            self.move(ui.window_x, ui.window_y)
        
        # Restore sidebar state
        if not ui.sidebar_visible:
            self.sidebar.hide()
            self.toggle_sidebar_action.setChecked(False)
        
        # Restore last model
        if self.config.last_model:
            self.sidebar.set_selected_model(self.config.last_model)
    
    def _save_window_state(self) -> None:
        """Save window size and position."""
        self.config.update_ui_settings(
            window_width=self.width(),
            window_height=self.height(),
            window_x=self.x(),
            window_y=self.y(),
            sidebar_visible=self.sidebar.isVisible()
        )
        self.config.save()
    
    @pyqtSlot(str)
    def _on_model_selected(self, model: str) -> None:
        """Handle model selection."""
        self.model_label.setText(f"Model: {model}")
        self.config.last_model = model
        self.config.save()
    
    @pyqtSlot()
    def _on_new_chat(self) -> None:
        """Start a new chat."""
        model = self.sidebar.get_selected_model()
        
        if not model:
            QMessageBox.warning(
                self,
                "No Model Selected",
                "Please select a model before starting a new chat.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Stop any running session
        if self.ollama.is_running:
            self.ollama.stop()
        
        # Create new conversation
        system_message = self.config.llm.system_message
        self._current_conversation = self.chat_history.create_conversation(
            title="New Chat",
            model=model,
            system_message=system_message
        )
        
        # Configure and start Ollama
        self.ollama.set_options(
            temperature=self.config.llm.temperature,
            top_p=self.config.llm.top_p,
            top_k=self.config.llm.top_k,
            repeat_penalty=self.config.llm.repeat_penalty,
            context_length=self.config.llm.context_length
        )
        self.ollama.set_system_message(system_message)
        
        if not self.ollama.start(model):
            QMessageBox.critical(
                self,
                "Failed to Start",
                f"Failed to start Ollama with model '{model}'.\n"
                "Make sure Ollama is running and the model is available.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Clear chat panel
        self.chat_panel.clear_for_chat()
        
        # Update sidebar
        self.sidebar.set_current_conversation(self._current_conversation.id)
        self.sidebar.refresh_history()
        
        # Enable input
        self.input_area.set_enabled(True)
        self.input_area.focus_input()
        
        self.status_label.setText("Ready")
    
    @pyqtSlot(int)
    def _on_conversation_selected(self, conv_id: int) -> None:
        """Load a conversation from history."""
        conversation = self.chat_history.get_conversation(conv_id)
        
        if not conversation:
            return
        
        # Stop current session
        if self.ollama.is_running:
            self.ollama.stop()
        
        self._current_conversation = conversation
        
        # Load messages into chat panel
        self.chat_panel.load_conversation(conversation.messages)
        
        # Configure and start Ollama with this conversation's model
        self.sidebar.set_selected_model(conversation.model)
        
        self.ollama.set_options(
            temperature=self.config.llm.temperature,
            top_p=self.config.llm.top_p,
            top_k=self.config.llm.top_k,
            repeat_penalty=self.config.llm.repeat_penalty,
            context_length=self.config.llm.context_length
        )
        self.ollama.set_system_message(conversation.system_message)
        
        if not self.ollama.start(conversation.model):
            QMessageBox.warning(
                self,
                "Model Not Available",
                f"Could not start model '{conversation.model}'.\n"
                "The model may have been deleted or Ollama is not running.",
                QMessageBox.StandardButton.Ok
            )
            self.input_area.set_enabled(False)
            return
        
        # Restore conversation context to Ollama so it remembers previous messages
        for msg in conversation.messages:
            self.ollama._messages.append({"role": msg.role, "content": msg.content})
        
        self.input_area.set_enabled(True)
        self.input_area.focus_input()
        
        self.model_label.setText(f"Model: {conversation.model}")
        self.status_label.setText("Ready")
    
    @pyqtSlot(int)
    def _on_conversation_deleted(self, conv_id: int) -> None:
        """Handle conversation deletion."""
        if self._current_conversation and self._current_conversation.id == conv_id:
            self._current_conversation = None
            self.chat_panel.clear()
            self.input_area.set_enabled(False)
            
            if self.ollama.is_running:
                self.ollama.stop()
    
    @pyqtSlot(str, list)
    def _on_message_sent(self, message: str, attachments: list) -> None:
        """Handle sending a message."""
        if not self._current_conversation:
            # Start a new chat first
            self._on_new_chat()
            if not self._current_conversation:
                return
        
        if not self.ollama.is_running:
            QMessageBox.warning(
                self,
                "No Active Session",
                "Please start a new chat or select an existing one.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        if self._is_generating:
            return
        
        self._is_generating = True
        self.input_area.set_enabled(False)
        self.status_label.setText("Generating...")

        # Show attachment names in transcript for traceability.
        message_for_display = message
        if attachments:
            attachment_lines = "\n".join(f"- {Path(p).name}" for p in attachments)
            if message_for_display.strip():
                message_for_display = f"{message_for_display}\n\nAttachments:\n{attachment_lines}"
            else:
                message_for_display = f"Attachments:\n{attachment_lines}"
        
        # Add user message to display and database
        self.chat_panel.add_message('user', message_for_display)
        self.chat_history.add_message(
            self._current_conversation.id,
            'user',
            message_for_display
        )
        
        # Update conversation title if it's the first message
        if len(self.chat_panel.get_messages()) == 1:
            title_source = message_for_display.strip() or "New Chat"
            title = title_source[:50] + ("..." if len(title_source) > 50 else "")
            self.chat_history.update_conversation_title(
                self._current_conversation.id,
                title
            )
            self.sidebar.refresh_history()
        
        # Start streaming response
        self.chat_panel.start_streaming('assistant')
        
        def on_token(token: str) -> None:
            # Update UI in main thread using invokeMethod for thread safety
            QMetaObject.invokeMethod(
                self.chat_panel,
                "append_streaming_token",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, token)
            )
        
        def on_complete() -> None:
            # Use signal for thread-safe callback to main thread
            self._generation_complete.emit()
        
        def on_error(error: str) -> None:
            # Use signal for thread-safe callback to main thread
            self._generation_error.emit(error)
        
        self.ollama.send_message(
            message,
            on_token,
            on_complete,
            on_error,
            attachments=attachments
        )
    
    @pyqtSlot()
    def _handle_generation_complete(self) -> None:
        """Handle generation completion in main thread."""
        content = self.chat_panel.finish_streaming()
        
        # Save to database
        if content.strip() and self._current_conversation:
            self.chat_history.add_message(
                self._current_conversation.id,
                'assistant',
                content
            )
        
        self._is_generating = False
        self.input_area.set_enabled(True)
        self.input_area.focus_input()
        self.status_label.setText("Ready")
    
    @pyqtSlot(str)
    def _handle_generation_error(self, error: str) -> None:
        """Handle generation error in main thread."""
        self.chat_panel.finish_streaming()
        self._is_generating = False
        self.input_area.set_enabled(True)
        self.status_label.setText("Error")
        
        QMessageBox.warning(
            self,
            "Error",
            f"Error during generation: {error}",
            QMessageBox.StandardButton.Ok
        )
    
    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    @pyqtSlot()
    def _on_settings_changed(self) -> None:
        """Handle settings change."""
        # Update Ollama options if running
        if self.ollama.is_running:
            self.ollama.set_options(
                temperature=self.config.llm.temperature,
                top_p=self.config.llm.top_p,
                top_k=self.config.llm.top_k,
                repeat_penalty=self.config.llm.repeat_penalty,
                context_length=self.config.llm.context_length
            )
    
    def _toggle_sidebar(self, checked: bool) -> None:
        """Toggle sidebar visibility."""
        self.sidebar.setVisible(checked)
    
    def _copy_last_response(self) -> None:
        """Copy the last assistant response to clipboard."""
        self.chat_panel.copy_last_response()
        self.statusbar.showMessage("Copied to clipboard", 2000)
    
    def _clear_current_chat(self) -> None:
        """Clear the current chat display."""
        if self._current_conversation:
            reply = QMessageBox.question(
                self,
                "Clear Chat",
                "Clear the current chat? Messages will be kept in history.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.chat_panel.clear_for_chat()
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About ForumLLM",
            "<h3>ForumLLM</h3>"
            "<p>A local LLM chat client with a nostalgic aesthetic.</p>"
            "<p>Built with PyQt6 and Ollama.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Chat with local LLMs via Ollama</li>"
            "<li>Local conversation history</li>"
            "<li>Customizable LLM parameters</li>"
            "<li>Markdown and code rendering</li>"
            "</ul>"
            "<p>All conversations stay on your machine.</p>"
        )
    
    def closeEvent(self, event) -> None:
        """Handle application close."""
        # Save window state
        self._save_window_state()
        
        # Stop Ollama
        if self.ollama.is_running:
            self.ollama.stop()
        
        # Close database
        self.chat_history.close()
        
        event.accept()
