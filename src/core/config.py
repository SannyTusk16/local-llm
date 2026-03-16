"""
ForumLLM - Configuration Management
Handles application settings persistence and defaults.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Optional
from pathlib import Path


@dataclass
class LLMSettings:
    """LLM generation parameters."""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    context_length: int = 4096
    system_message: str = "You are a helpful assistant."


@dataclass
class UISettings:
    """UI-related settings."""
    window_width: int = 1200
    window_height: int = 800
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    sidebar_visible: bool = True
    sidebar_width: int = 280
    font_size: int = 12


@dataclass
class AppConfig:
    """Main application configuration."""
    last_model: str = ""
    llm: LLMSettings = field(default_factory=LLMSettings)
    ui: UISettings = field(default_factory=UISettings)
    
    # System message presets for quick access
    system_presets: dict = field(default_factory=lambda: {
        "Default": "You are a helpful assistant.",
        "Concise": "You are a helpful assistant. Keep answers brief and to the point.",
        "Technical": "You are a senior software engineer. Provide detailed technical explanations with code examples when appropriate.",
        "Creative Writer": "You are a creative writer. Be imaginative and expressive in your responses.",
        "Socratic": "You are a Socratic teacher. Answer questions with guiding questions to help the user discover answers themselves."
    })


class Config:
    """Configuration manager with file persistence."""
    
    DEFAULT_CONFIG_DIR = Path.home() / ".forumllm"
    CONFIG_FILENAME = "config.json"
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / self.CONFIG_FILENAME
        self._config: AppConfig = AppConfig()
        self._ensure_config_dir()
        self.load()
    
    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._config = self._dict_to_config(data)
            except (json.JSONDecodeError, KeyError) as e:
                # Corrupted config, use defaults
                print(f"Warning: Config load failed, using defaults: {e}")
                self._config = AppConfig()
    
    def save(self) -> None:
        """Save configuration to file."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config_to_dict(self._config), f, indent=2)
    
    def _config_to_dict(self, config: AppConfig) -> dict:
        """Convert config dataclass to dict."""
        return {
            'last_model': config.last_model,
            'llm': asdict(config.llm),
            'ui': asdict(config.ui),
            'system_presets': config.system_presets
        }
    
    def _dict_to_config(self, data: dict) -> AppConfig:
        """Convert dict to config dataclass."""
        return AppConfig(
            last_model=data.get('last_model', ''),
            llm=LLMSettings(**data.get('llm', {})),
            ui=UISettings(**data.get('ui', {})),
            system_presets=data.get('system_presets', AppConfig().system_presets)
        )
    
    @property
    def llm(self) -> LLMSettings:
        """Get LLM settings."""
        return self._config.llm
    
    @property
    def ui(self) -> UISettings:
        """Get UI settings."""
        return self._config.ui
    
    @property
    def last_model(self) -> str:
        """Get last used model."""
        return self._config.last_model
    
    @last_model.setter
    def last_model(self, value: str) -> None:
        """Set last used model."""
        self._config.last_model = value
    
    @property
    def system_presets(self) -> dict:
        """Get system message presets."""
        return self._config.system_presets
    
    def add_system_preset(self, name: str, message: str) -> None:
        """Add a new system message preset."""
        self._config.system_presets[name] = message
    
    def remove_system_preset(self, name: str) -> None:
        """Remove a system message preset."""
        if name in self._config.system_presets:
            del self._config.system_presets[name]
    
    def update_llm_settings(self, **kwargs) -> None:
        """Update LLM settings."""
        for key, value in kwargs.items():
            if hasattr(self._config.llm, key):
                setattr(self._config.llm, key, value)
    
    def update_ui_settings(self, **kwargs) -> None:
        """Update UI settings."""
        for key, value in kwargs.items():
            if hasattr(self._config.ui, key):
                setattr(self._config.ui, key, value)
    
    def get_data_dir(self) -> Path:
        """Get the data directory path."""
        data_dir = self.config_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
