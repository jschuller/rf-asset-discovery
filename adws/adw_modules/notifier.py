"""Notification backends for spectrum watch alerts.

Supports multiple notification targets:
- ntfy.sh - Push notifications via HTTP
- Console - Rich formatted terminal output
- Multi-backend - Send to multiple targets concurrently
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class NotificationPriority(IntEnum):
    """Notification priority levels (maps to ntfy priority 1-5)."""

    LOW = 1
    MEDIUM = 2
    DEFAULT = 3
    HIGH = 4
    URGENT = 5


@dataclass
class Notification:
    """A notification to be sent via notification backends."""

    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.DEFAULT
    timestamp: datetime = field(default_factory=datetime.now)
    tags: list[str] = field(default_factory=list)
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "message": self.message,
            "priority": self.priority.name,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "data": self.data,
        }


@runtime_checkable
class NotificationBackend(Protocol):
    """Protocol for notification backends."""

    async def send(self, notification: Notification) -> bool:
        """Send a notification.

        Args:
            notification: The notification to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        ...


class NtfyBackend:
    """Notification backend using ntfy.sh.

    ntfy.sh is a simple HTTP-based pub-sub notification service.
    Notifications can be received via mobile app, web, or CLI.

    Example:
        >>> backend = NtfyBackend("my-sdr-alerts")
        >>> await backend.send(Notification(
        ...     title="New Signal",
        ...     message="Signal detected at 121.5 MHz",
        ...     priority=NotificationPriority.HIGH,
        ...     tags=["radio", "emergency"],
        ... ))
    """

    def __init__(
        self,
        topic: str,
        server: str = "https://ntfy.sh",
        auth_token: str | None = None,
    ) -> None:
        """Initialize ntfy.sh backend.

        Args:
            topic: The ntfy topic to publish to.
            server: ntfy server URL (default: https://ntfy.sh).
            auth_token: Optional auth token for private topics.
        """
        self.topic = topic
        self.server = server.rstrip("/")
        self.auth_token = auth_token
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Get or create HTTP client lazily."""
        if self._client is None:
            try:
                import httpx

                self._client = httpx.AsyncClient(timeout=30.0)
            except ImportError:
                logger.error("httpx not installed. Run: pip install httpx")
                raise RuntimeError("httpx required for ntfy.sh notifications")
        return self._client

    async def send(self, notification: Notification) -> bool:
        """Send notification via ntfy.sh.

        Args:
            notification: The notification to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            client = await self._get_client()
            url = f"{self.server}/{self.topic}"

            headers: dict[str, str] = {
                "Title": notification.title,
                "Priority": str(notification.priority.value),
            }

            if notification.tags:
                headers["Tags"] = ",".join(notification.tags)

            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            # Include data as JSON if present
            if notification.data:
                import json

                headers["X-Data"] = json.dumps(notification.data)

            response = await client.post(
                url,
                content=notification.message,
                headers=headers,
            )

            if response.status_code == 200:
                logger.debug("Notification sent to ntfy.sh/%s", self.topic)
                return True
            else:
                logger.warning(
                    "ntfy.sh returned %d: %s",
                    response.status_code,
                    response.text,
                )
                return False

        except Exception as e:
            logger.error("Failed to send ntfy notification: %s", e)
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class ConsoleBackend:
    """Notification backend for terminal output.

    Uses Rich for formatted output when available, falls back to plain text.
    """

    # ANSI color codes for priority levels
    PRIORITY_COLORS = {
        NotificationPriority.LOW: "\033[90m",  # Gray
        NotificationPriority.MEDIUM: "\033[37m",  # White
        NotificationPriority.DEFAULT: "\033[36m",  # Cyan
        NotificationPriority.HIGH: "\033[33m",  # Yellow
        NotificationPriority.URGENT: "\033[31m",  # Red
    }
    RESET = "\033[0m"

    def __init__(self, use_rich: bool = True) -> None:
        """Initialize console backend.

        Args:
            use_rich: Whether to use Rich for formatting (if available).
        """
        self.use_rich = use_rich
        self._console: Any = None

    def _get_console(self) -> Any:
        """Get Rich console if available."""
        if self._console is None and self.use_rich:
            try:
                from rich.console import Console

                self._console = Console()
            except ImportError:
                self.use_rich = False
        return self._console

    async def send(self, notification: Notification) -> bool:
        """Send notification to console.

        Args:
            notification: The notification to send.

        Returns:
            Always True (console output doesn't fail).
        """
        console = self._get_console()
        timestamp = notification.timestamp.strftime("%H:%M:%S")

        if console and self.use_rich:
            from rich.panel import Panel
            from rich.text import Text

            # Map priority to Rich style
            style_map = {
                NotificationPriority.LOW: "dim",
                NotificationPriority.MEDIUM: "white",
                NotificationPriority.DEFAULT: "cyan",
                NotificationPriority.HIGH: "yellow bold",
                NotificationPriority.URGENT: "red bold",
            }
            style = style_map.get(notification.priority, "white")

            # Build content
            content = Text()
            content.append(f"{notification.message}\n\n", style=style)

            if notification.tags:
                content.append("Tags: ", style="dim")
                content.append(", ".join(notification.tags), style="blue")
                content.append("\n")

            content.append(f"[{timestamp}]", style="dim")

            panel = Panel(
                content,
                title=f"[bold]{notification.title}[/bold]",
                border_style=style,
                expand=False,
            )
            console.print(panel)

        else:
            # Plain text fallback
            color = self.PRIORITY_COLORS.get(notification.priority, "")
            priority_name = notification.priority.name

            print(f"\n{color}{'='*50}{self.RESET}")
            print(f"{color}[{priority_name}] {notification.title}{self.RESET}")
            print(f"{'='*50}")
            print(notification.message)
            if notification.tags:
                print(f"Tags: {', '.join(notification.tags)}")
            print(f"[{timestamp}]")
            print()

        return True


class MultiBackend:
    """Send notifications to multiple backends concurrently.

    Example:
        >>> multi = MultiBackend([
        ...     NtfyBackend("my-topic"),
        ...     ConsoleBackend(),
        ... ])
        >>> results = await multi.send(notification)
        >>> print(f"Sent to {sum(results)}/{len(results)} backends")
    """

    def __init__(self, backends: list[NotificationBackend]) -> None:
        """Initialize multi-backend.

        Args:
            backends: List of backends to send to.
        """
        self.backends = backends

    async def send(self, notification: Notification) -> list[bool]:
        """Send notification to all backends concurrently.

        Args:
            notification: The notification to send.

        Returns:
            List of success/failure for each backend.
        """
        if not self.backends:
            logger.warning("No notification backends configured")
            return []

        tasks = [backend.send(notification) for backend in self.backends]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to False
        return [r if isinstance(r, bool) else False for r in results]

    def add_backend(self, backend: NotificationBackend) -> None:
        """Add a backend to the list."""
        self.backends.append(backend)

    async def close(self) -> None:
        """Close all backends that support it."""
        for backend in self.backends:
            if hasattr(backend, "close"):
                await backend.close()


def create_notifier(
    ntfy_topic: str | None = None,
    ntfy_server: str = "https://ntfy.sh",
    console: bool = True,
    use_rich: bool = True,
) -> MultiBackend:
    """Create a configured multi-backend notifier.

    Convenience function for common configuration.

    Args:
        ntfy_topic: ntfy.sh topic name (None to disable).
        ntfy_server: ntfy server URL.
        console: Whether to include console output.
        use_rich: Whether to use Rich formatting for console.

    Returns:
        Configured MultiBackend instance.
    """
    backends: list[NotificationBackend] = []

    if ntfy_topic:
        backends.append(NtfyBackend(ntfy_topic, ntfy_server))

    if console:
        backends.append(ConsoleBackend(use_rich=use_rich))

    return MultiBackend(backends)
