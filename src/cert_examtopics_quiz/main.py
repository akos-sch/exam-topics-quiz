"""Main application logic for cert-examtopics-quiz."""

from rich.console import Console

from .questionnaire.cli import CLIInterface

console = Console()


def main() -> None:
    """Main application entry point - runs the quiz interface."""
    try:
        cli = CLIInterface()
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted by user.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
