"""
ForumLLM - OpenClaw Wrapper
Routes selected prompts to OpenClaw CLI when they likely require automation/tools.
"""

import subprocess
import threading
import shutil
import os
from pathlib import Path
from typing import Callable, Optional, List


class OpenClawWrapper:
    """Minimal OpenClaw bridge for tool-heavy prompts."""

    # Heuristic trigger words for requests that likely need OpenClaw tool use.
    TOOL_KEYWORDS = {
        "email", "gmail", "calendar", "schedule", "remind", "reminder",
        "browser", "browse", "website", "scrape", "search web", "research online",
        "telegram", "whatsapp", "discord", "slack", "signal", "imessage",
        "run command", "terminal", "shell", "script", "automate", "automation",
        "github", "create issue", "open pr", "pull request", "cron", "task",
        "call", "message someone", "send message", "check inbox"
    }

    # Phrases indicating the user expects access to local machine/filesystem tools.
    LOCAL_TOOL_HINTS = {
        "downloads folder", "desktop folder", "documents folder", "my computer",
        "local computer", "local machine", "file system", "filesystem", "this machine",
        "count files", "count images", "find files", "list files", "scan folder",
        "in my folder", "on my machine", "on my computer"
    }

    def __init__(self):
        self._running = False
        self._agent_name = ""
        self._session_id = ""
        self._to_target = ""

    def set_targets(
        self,
        agent_name: Optional[str] = None,
        session_id: Optional[str] = None,
        to_target: Optional[str] = None,
    ) -> None:
        """Set OpenClaw routing targets used when the CLI requires session selection."""
        if agent_name is not None:
            self._agent_name = agent_name.strip()
        if session_id is not None:
            self._session_id = session_id.strip()
        if to_target is not None:
            self._to_target = to_target.strip()

    @staticmethod
    def _resolve_command() -> Optional[List[str]]:
        """Resolve an executable command for invoking OpenClaw."""
        if shutil.which("openclaw"):
            return ["openclaw"]

        if shutil.which("npx"):
            return ["npx", "-y", "openclaw@latest"]

        return None

    @staticmethod
    def is_available() -> bool:
        """Check whether OpenClaw CLI is installed."""
        return OpenClawWrapper._resolve_command() is not None

    def should_handle_prompt(self, message: str) -> bool:
        """Return True if prompt likely needs OpenClaw capabilities."""
        text = message.lower().strip()
        if not text:
            return False

        # Fast explicit override words
        if (
            "use openclaw" in text
            or "with openclaw" in text
            or text.startswith("openclaw:")
            or text.startswith("/openclaw")
        ):
            return True

        # Common prompts that require direct machine/file access should use OpenClaw.
        if any(hint in text for hint in self.LOCAL_TOOL_HINTS):
            return True

        # Handle common filesystem action + target combinations without exact phrase matches.
        fs_actions = ("count", "find", "list", "scan", "check")
        fs_targets = ("image", "images", "file", "files", "folder", "directory", "downloads")
        if any(action in text for action in fs_actions) and any(target in text for target in fs_targets):
            return True

        return any(keyword in text for keyword in self.TOOL_KEYWORDS)

    def _build_message(self, message: str, attachments: Optional[List[str]] = None) -> str:
        """Append lightweight attachment context for OpenClaw."""
        if not attachments:
            return message

        lines = []
        for raw in attachments:
            path = Path(raw)
            lines.append(f"- {path.name}: {path}")

        attachment_context = "\n".join(lines)
        return (
            f"{message}\n\n"
            "Attached files are available locally on this machine:\n"
            f"{attachment_context}"
        )

    def send_message(
        self,
        message: str,
        on_token: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None],
        attachments: Optional[List[str]] = None,
    ) -> None:
        """Send a prompt to OpenClaw in a worker thread."""
        if self._running:
            on_error("OpenClaw is busy")
            return

        if not self.is_available():
            on_error(
                "OpenClaw CLI is not available. Install with 'npm install -g openclaw@latest' "
                "or ensure 'npx' is installed."
            )
            return

        self._running = True

        def run_openclaw() -> None:
            try:
                final_message = self._build_message(message, attachments)
                command_prefix = self._resolve_command()
                if not command_prefix:
                    on_error("OpenClaw command could not be resolved")
                    return

                # Build supported command variants for session targeting.
                # OpenClaw may require one of: --to, --session-id, or --agent <name>.
                configured_agent = self._agent_name or (os.getenv("OPENCLAW_AGENT") or "").strip()
                configured_session = self._session_id or (os.getenv("OPENCLAW_SESSION_ID") or "").strip()
                configured_to = self._to_target or (os.getenv("OPENCLAW_TO") or "").strip()

                commands_to_try = []
                if configured_agent:
                    commands_to_try.append(
                        [*command_prefix, "agent", "--agent", configured_agent, "--message", final_message]
                    )
                if configured_session:
                    commands_to_try.append(
                        [*command_prefix, "agent", "--session-id", configured_session, "--message", final_message]
                    )
                if configured_to:
                    commands_to_try.append(
                        [*command_prefix, "agent", "--to", configured_to, "--message", final_message]
                    )

                # Default attempt for CLIs that can infer a target session.
                commands_to_try.append([*command_prefix, "agent", "--message", final_message])

                result = None
                stdout = ""
                stderr = ""

                for command in commands_to_try:
                    candidate = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        check=False,
                    )

                    candidate_stdout = (candidate.stdout or "").strip()
                    candidate_stderr = (candidate.stderr or "").strip()

                    # Success path.
                    if candidate.returncode == 0:
                        result = candidate
                        stdout = candidate_stdout
                        stderr = candidate_stderr
                        break

                    # If this version requires a selected session and none is configured,
                    # stop early with setup guidance.
                    candidate_detail = (candidate_stderr or candidate_stdout or "").lower()
                    if (
                        "pass --to" in candidate_detail
                        and "--session-id" in candidate_detail
                        and "--agent" in candidate_detail
                        and not (configured_agent or configured_session or configured_to)
                    ):
                        on_error(
                            "OpenClaw needs a target session/agent. Configure OpenClaw settings "
                            "(Agent, Session ID, or To target) or set OPENCLAW_AGENT/OPENCLAW_SESSION_ID/OPENCLAW_TO."
                        )
                        return

                    result = candidate
                    stdout = candidate_stdout
                    stderr = candidate_stderr

                if result is None or result.returncode != 0:
                    detail = stderr or stdout or (
                        f"exit code {result.returncode}" if result else "unknown failure"
                    )
                    if "pass --to" in detail.lower() and "--session-id" in detail.lower():
                        on_error(
                            "OpenClaw needs a target session/agent. Run OpenClaw setup first "
                            "or configure a default agent/session in your OpenClaw CLI profile."
                        )
                        return
                    on_error(f"OpenClaw command failed: {detail}")
                    return

                if not stdout:
                    on_error("OpenClaw returned no output")
                    return

                on_token(stdout)
                on_complete()
            except subprocess.TimeoutExpired:
                on_error("OpenClaw timed out while processing your request")
            except Exception as e:
                on_error(f"OpenClaw error: {e}")
            finally:
                self._running = False

        thread = threading.Thread(target=run_openclaw, daemon=True)
        thread.start()

    @property
    def is_running(self) -> bool:
        """Whether OpenClaw bridge is currently processing a request."""
        return self._running
