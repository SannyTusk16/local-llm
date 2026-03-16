"""
ForumLLM - Ollama HTTP API Runner
Communicates with local Ollama server at localhost:11434.
All traffic stays on your machine - nothing leaves your computer.
"""

import json
import threading
import urllib.request
import urllib.error
from typing import Callable, Optional, List, Dict
from dataclasses import dataclass


OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class OllamaModel:
    """Represents an installed Ollama model."""
    name: str
    size: str
    modified: str
    
    def __str__(self) -> str:
        return f"{self.name} ({self.size})"


class OllamaRunner:
    """
    Manages Ollama interactions via local HTTP API.
    All communication is with localhost - nothing leaves your machine.
    """
    
    def __init__(self):
        self._model: Optional[str] = None
        self._running = False
        self._system_message: Optional[str] = None
        self._options: dict = {}
        self._messages: List[Dict[str, str]] = []
        self._cancel_flag = False
    
    @staticmethod
    def is_ollama_installed() -> bool:
        """Check if Ollama server is running on localhost."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
    
    @staticmethod
    def list_models() -> List[OllamaModel]:
        """List all locally available Ollama models."""
        try:
            req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
            
            models = []
            for model in data.get("models", []):
                name = model.get("name", "unknown")
                size_bytes = model.get("size", 0)
                if size_bytes >= 1e9:
                    size = f"{size_bytes / 1e9:.1f} GB"
                elif size_bytes >= 1e6:
                    size = f"{size_bytes / 1e6:.1f} MB"
                else:
                    size = f"{size_bytes} B"
                modified = model.get("modified_at", "unknown")[:10]
                models.append(OllamaModel(name=name, size=size, modified=modified))
            return models
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def set_options(self, **options) -> None:
        """Set generation options (temperature, top_p, etc.)."""
        self._options = options
    
    def set_system_message(self, message: str) -> None:
        """Set the system message for the conversation."""
        self._system_message = message
    
    def start(self, model: str) -> bool:
        """Start a new conversation with the specified model."""
        self.stop()
        self._model = model
        self._running = True
        self._cancel_flag = False
        self._messages = []
        if self._system_message:
            self._messages.append({"role": "system", "content": self._system_message})
        return self.is_ollama_installed()
    
    def send_message(
        self,
        message: str,
        on_token: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None]
    ) -> None:
        """Send a message and stream the response."""
        print(f"[DEBUG] send_message called, running={self._running}, model={self._model}")
        if not self._running:
            print("[DEBUG] Session not running!")
            on_error("Session not started")
            return
        
        self._cancel_flag = False
        self._messages.append({"role": "user", "content": message})
        print(f"[DEBUG] Starting stream thread for: {message[:50]}...")
        
        def stream_response():
            try:
                payload = {
                    "model": self._model,
                    "messages": self._messages,
                    "stream": True,
                    "options": {}
                }
                
                if self._options.get("temperature") is not None:
                    payload["options"]["temperature"] = self._options["temperature"]
                if self._options.get("top_p") is not None:
                    payload["options"]["top_p"] = self._options["top_p"]
                if self._options.get("top_k") is not None:
                    payload["options"]["top_k"] = self._options["top_k"]
                if self._options.get("repeat_penalty") is not None:
                    payload["options"]["repeat_penalty"] = self._options["repeat_penalty"]
                if self._options.get("context_length") is not None:
                    payload["options"]["num_ctx"] = self._options["context_length"]
                
                req = urllib.request.Request(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                full_response = []
                print(f"[DEBUG] Sending to {self._model}: {message[:50]}...")
                
                with urllib.request.urlopen(req, timeout=300) as response:
                    for line in response:
                        if self._cancel_flag:
                            break
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line.decode("utf-8"))
                            
                            # Extract content from message
                            if "message" in data:
                                msg = data["message"]
                                token = msg.get("content", "")
                                
                                # Only send non-empty tokens
                                if token:
                                    full_response.append(token)
                                    print(token, end="", flush=True)
                                    on_token(token)
                                
                                # Check for thinking/reasoning content (for models like deepseek-r1)
                                if "reasoning" in msg and msg["reasoning"]:
                                    print(f"\n[THINKING] {msg['reasoning']}")
                            
                            if data.get("done", False):
                                print("\n[DONE]")
                                break
                        except json.JSONDecodeError as e:
                            print(f"[DEBUG-OLLAMA] JSON decode error: {e}")
                            continue
                
                assistant_message = "".join(full_response)
                print(f"[DEBUG] Response complete: {len(assistant_message)} chars")
                if assistant_message:
                    self._messages.append({"role": "assistant", "content": assistant_message})
                
                on_complete()
                
            except urllib.error.URLError as e:
                print(f"[DEBUG] URL Error: {e.reason}")
                on_error(f"Connection error: {e.reason}. Is Ollama running?")
            except Exception as e:
                print(f"[DEBUG] Exception: {e}")
                on_error(str(e))
        
        thread = threading.Thread(target=stream_response, daemon=True)
        thread.start()
    
    def stop(self) -> None:
        """Stop the current session."""
        self._cancel_flag = True
        self._running = False
        self._messages = []
    
    def cancel_generation(self) -> None:
        """Cancel current generation without stopping session."""
        self._cancel_flag = True
    
    @property
    def is_running(self) -> bool:
        """Check if a session is active."""
        return self._running
    
    @property
    def current_model(self) -> Optional[str]:
        """Get the current model name."""
        return self._model if self._running else None
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return self._messages.copy()
    
    def clear_history(self) -> None:
        """Clear conversation history but keep session active."""
        self._messages = []
        if self._system_message:
            self._messages.append({"role": "system", "content": self._system_message})
