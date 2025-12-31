"""Rich terminal display functions for SDR Toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if TYPE_CHECKING:
    from sdr_toolkit.apps.scanner import ScanResult


# Global console instance
_console: Console | None = None


def get_console() -> Console:
    """Get the global rich console instance."""
    global _console
    if _console is None:
        if RICH_AVAILABLE:
            _console = Console()
        else:
            raise ImportError("rich library not installed. Install with: pip install rich")
    return _console


def print_banner(title: str, subtitle: str | None = None) -> None:
    """Print a styled banner.

    Args:
        title: Main title text.
        subtitle: Optional subtitle.
    """
    if not RICH_AVAILABLE:
        print(f"\n{'=' * 50}")
        print(f"  {title}")
        if subtitle:
            print(f"  {subtitle}")
        print(f"{'=' * 50}\n")
        return

    console = get_console()
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")
    console.print(Panel(text, border_style="cyan"))


def print_success(message: str) -> None:
    """Print a success message.

    Args:
        message: Message to display.
    """
    if not RICH_AVAILABLE:
        print(f"[OK] {message}")
        return

    console = get_console()
    console.print(f"[bold green]✓[/] {message}")


def print_warning(message: str) -> None:
    """Print a warning message.

    Args:
        message: Message to display.
    """
    if not RICH_AVAILABLE:
        print(f"[WARNING] {message}")
        return

    console = get_console()
    console.print(f"[bold yellow]⚠[/] {message}")


def print_error(message: str) -> None:
    """Print an error message.

    Args:
        message: Message to display.
    """
    if not RICH_AVAILABLE:
        print(f"[ERROR] {message}")
        return

    console = get_console()
    console.print(f"[bold red]✗[/] {message}")


def display_scan_results(
    result: ScanResult,
    max_signals: int = 25,
    show_all: bool = False,
) -> None:
    """Display spectrum scan results in a rich table.

    Args:
        result: ScanResult object from SpectrumScanner.
        max_signals: Maximum number of signals to display.
        show_all: If True, show all signals regardless of max_signals.
    """
    if not RICH_AVAILABLE:
        # Fallback to basic output
        print(f"\nScan completed in {result.scan_time_seconds:.1f} seconds")
        print(f"Noise floor: {result.noise_floor_db:.1f} dB")
        print(f"Signals found: {len(result.peaks)}\n")

        if result.peaks:
            sorted_peaks = sorted(result.peaks, key=lambda p: p.power_db, reverse=True)
            print("Detected signals (sorted by power):")
            print("-" * 50)
            for i, peak in enumerate(sorted_peaks[:max_signals], 1):
                above_noise = peak.power_db - result.noise_floor_db
                print(
                    f"{i:4}  {peak.frequency_hz/1e6:10.3f} MHz  "
                    f"{peak.power_db:+7.1f} dB  {above_noise:+7.1f} dB above noise"
                )
            if len(sorted_peaks) > max_signals and not show_all:
                print(f"... and {len(sorted_peaks) - max_signals} more signals")
        return

    console = get_console()

    # Summary panel
    summary = Text()
    summary.append("Scan Time: ", style="dim")
    summary.append(f"{result.scan_time_seconds:.1f}s\n", style="cyan")
    summary.append("Noise Floor: ", style="dim")
    summary.append(f"{result.noise_floor_db:.1f} dB\n", style="yellow")
    summary.append("Signals Found: ", style="dim")
    summary.append(f"{len(result.peaks)}", style="bold green")

    console.print(Panel(summary, title="[bold]Scan Results[/]", border_style="green"))

    if not result.peaks:
        console.print("[dim]No signals detected above threshold.[/]")
        return

    # Create signals table
    table = Table(
        title="Detected Signals",
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("#", justify="right", style="dim", width=4)
    table.add_column("Frequency", justify="right", style="cyan")
    table.add_column("Power", justify="right", style="green")
    table.add_column("Above Noise", justify="right", style="yellow")
    table.add_column("Band", justify="left", style="dim")

    # Sort by power
    sorted_peaks = sorted(result.peaks, key=lambda p: p.power_db, reverse=True)

    # Display signals
    display_count = len(sorted_peaks) if show_all else min(max_signals, len(sorted_peaks))
    for i, peak in enumerate(sorted_peaks[:display_count], 1):
        freq_mhz = peak.frequency_hz / 1e6
        above_noise = peak.power_db - result.noise_floor_db

        # Identify band
        band = _identify_band(freq_mhz)

        table.add_row(
            str(i),
            f"{freq_mhz:.3f} MHz",
            f"{peak.power_db:+.1f} dB",
            f"{above_noise:+.1f} dB",
            band,
        )

    console.print(table)

    if len(sorted_peaks) > display_count:
        console.print(
            f"[dim]... and {len(sorted_peaks) - display_count} more signals "
            f"(use --all to show all)[/]"
        )


def display_signal_info(
    frequency_mhz: float,
    power_db: float,
    noise_floor_db: float | None = None,
    sample_rate: float | None = None,
) -> None:
    """Display information about a single signal.

    Args:
        frequency_mhz: Signal frequency in MHz.
        power_db: Signal power in dB.
        noise_floor_db: Optional noise floor in dB.
        sample_rate: Optional sample rate in Hz.
    """
    if not RICH_AVAILABLE:
        print(f"\nSignal: {frequency_mhz:.3f} MHz")
        print(f"Power: {power_db:.1f} dB")
        if noise_floor_db is not None:
            print(f"Above noise: {power_db - noise_floor_db:.1f} dB")
        if sample_rate is not None:
            print(f"Sample rate: {sample_rate/1e6:.3f} MHz")
        return

    console = get_console()

    band = _identify_band(frequency_mhz)

    info = Text()
    info.append("Frequency: ", style="dim")
    info.append(f"{frequency_mhz:.3f} MHz", style="bold cyan")
    if band:
        info.append(f" ({band})", style="dim")
    info.append("\n")

    info.append("Power: ", style="dim")
    info.append(f"{power_db:.1f} dB", style="green")
    info.append("\n")

    if noise_floor_db is not None:
        above_noise = power_db - noise_floor_db
        info.append("Above Noise: ", style="dim")
        info.append(f"{above_noise:.1f} dB", style="yellow")
        info.append("\n")

    if sample_rate is not None:
        info.append("Sample Rate: ", style="dim")
        info.append(f"{sample_rate/1e6:.3f} MHz", style="magenta")

    console.print(Panel(info, title="[bold]Signal Info[/]", border_style="blue"))


def _identify_band(freq_mhz: float) -> str:
    """Identify the radio band for a frequency.

    Args:
        freq_mhz: Frequency in MHz.

    Returns:
        Band name or empty string if unknown.
    """
    if 87.5 <= freq_mhz <= 108.0:
        return "FM Broadcast"
    elif 118.0 <= freq_mhz <= 137.0:
        return "Aircraft"
    elif 137.0 <= freq_mhz <= 138.0:
        return "NOAA Satellite"
    elif 144.0 <= freq_mhz <= 148.0:
        return "Amateur 2m"
    elif 156.0 <= freq_mhz <= 162.0:
        return "Marine VHF"
    elif 162.4 <= freq_mhz <= 162.55:
        return "NOAA Weather"
    elif 420.0 <= freq_mhz <= 450.0:
        return "Amateur 70cm"
    elif 462.0 <= freq_mhz <= 467.0:
        return "FRS/GMRS"
    elif 470.0 <= freq_mhz <= 608.0:
        return "UHF TV"
    else:
        return ""


def create_progress() -> Progress:
    """Create a progress bar for long operations.

    Returns:
        Rich Progress instance.
    """
    if not RICH_AVAILABLE:
        raise ImportError("rich library not installed")

    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=get_console(),
    )
