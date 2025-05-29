"""Command-line interface for cert-examtopics-quiz."""

import logging
import re
from datetime import datetime
from pathlib import Path

import typer
from bs4 import BeautifulSoup
from rich.console import Console
from tqdm import tqdm

from . import __version__
from .extractor import ExamTopicsScraper, QuestionParser, StorageManager
from .models.extraction import ExamInfo, ExtractionReport
from .questionnaire.cli import CLIInterface
from .utils.auth import validate_authentication

app = typer.Typer(
    name="cert-examtopics-quiz",
    help="A quiz application for certificate exam topics",
    add_completion=False,
)
console = Console()


@app.command()
def quiz(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
) -> None:
    """Start an interactive quiz session."""
    setup_logging(verbose, debug)

    try:
        cli = CLIInterface()
        cli.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Quiz cancelled by user.[/yellow]")
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def extract(
    exam_url: str = typer.Argument(..., help="URL of the exam to extract"),
    exam_name: str = typer.Option(
        None, "--name", help="Name for the exam (auto-generated if not provided)"
    ),
    max_questions: int = typer.Option(
        None, "--max-questions", help="Maximum number of questions to extract"
    ),
    extract_discussions: bool = typer.Option(
        True, "--discussions/--no-discussions", help="Extract discussion data"
    ),
    username: str = typer.Option(
        None, "--username", "-u", help="ExamTopics username/email"
    ),
    password: str = typer.Option(None, "--password", "-p", help="ExamTopics password"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
) -> None:
    """Extract exam data from ExamTopics website."""
    setup_logging(verbose, debug)

    try:
        # Validate authentication
        auth_valid, auth_error = validate_authentication()
        if not auth_valid:
            console.print(f"[red]❌ Authentication error: {auth_error}[/red]")
            console.print(
                "[dim]Please run 'gcloud auth application-default login' to authenticate.[/dim]"
            )
            raise typer.Exit(1)

        # Generate exam name if not provided
        if not exam_name:
            from urllib.parse import urlparse

            parsed = urlparse(exam_url)
            path_parts = [p for p in parsed.path.split("/") if p]
            exam_name = "-".join(path_parts[-2:]) if len(path_parts) >= 2 else "exam"

        console.print(f"[bold blue]🔍 Extracting exam: {exam_name}[/bold blue]")
        console.print(f"[dim]URL: {exam_url}[/dim]")
        console.print()

        # Initialize components
        scraper = ExamTopicsScraper(exam_url)
        parser = QuestionParser()
        storage = StorageManager()

        # Handle authentication if credentials provided
        if username and password:
            console.print("[dim]Logging in to ExamTopics...[/dim]")
            success, message = scraper.login(username, password)
            if success:
                console.print(f"[green]✓ {message}[/green]")
            else:
                console.print(f"[red]❌ Login failed: {message}[/red]")
                console.print(
                    "[dim]Continuing without authentication (limited access)...[/dim]"
                )
        elif username or password:
            console.print(
                "[yellow]⚠️ Both username and password are required for authentication[/yellow]"
            )
        else:
            console.print(
                "[yellow]⚠️ No credentials provided - accessing public content only[/yellow]"
            )
            console.print(
                "[dim]Use --username and --password for full access to questions[/dim]"
            )

        # Show authentication status
        auth_status = scraper.get_auth_status()
        if auth_status.get("authenticated") == "True":
            console.print(
                f"[green]Authenticated as: {auth_status.get('username', 'Unknown')}[/green]"
            )
        else:
            console.print(
                "[yellow]Not authenticated - may encounter captcha or limited content[/yellow]"
            )

        start_time = datetime.now()
        extraction_errors = []
        questions_extracted = 0
        discussions_extracted = 0

        try:
            # Get all pages for the exam
            console.print("[dim]Discovering exam pages...[/dim]")
            page_urls = scraper.get_exam_pages(exam_url)
            console.print(f"[green]Found {len(page_urls)} pages[/green]")

            # Extract questions from each page
            for page_num, page_url in enumerate(
                tqdm(page_urls, desc="Processing pages", unit="page"), 1
            ):
                try:
                    question_cards = scraper.get_question_cards(page_url)

                    for card in question_cards:
                        try:
                            question = parser.parse_question_card(
                                card, page_url, page_num
                            )
                            if question:
                                storage.save_question(question, exam_name)
                                questions_extracted += 1

                                # Extract discussion if enabled
                                if extract_discussions:
                                    # This would need additional implementation for discussion extraction
                                    pass

                                if (
                                    max_questions
                                    and questions_extracted >= max_questions
                                ):
                                    console.print(
                                        f"[yellow]Reached maximum questions limit: {max_questions}[/yellow]"
                                    )
                                    break

                        except Exception as e:
                            error_msg = (
                                f"Failed to extract question from page {page_num}: {e}"
                            )
                            extraction_errors.append(error_msg)
                            if verbose:
                                console.print(f"[red]❌ {error_msg}[/red]")

                    if max_questions and questions_extracted >= max_questions:
                        break

                except Exception as e:
                    error_msg = f"Failed to process page {page_num}: {e}"
                    extraction_errors.append(error_msg)
                    console.print(f"[red]❌ {error_msg}[/red]")

            # Save exam metadata
            exam_info = ExamInfo(
                name=exam_name,
                vendor="ExamTopics",
                code=exam_name,
                total_questions=questions_extracted,
                url=exam_url,
                last_updated=datetime.now(),
            )
            storage.save_exam_metadata(exam_info, exam_name)

            # Create extraction report
            end_time = datetime.now()
            report = ExtractionReport(
                exam_info=exam_info,
                questions_extracted=questions_extracted,
                discussions_extracted=discussions_extracted,
                extraction_errors=extraction_errors,
                start_time=start_time,
                end_time=end_time,
                success=questions_extracted > 0,
            )
            storage.save_extraction_report(report, exam_name)

            # Display results
            console.print()
            if report.success:
                console.print("[green]✅ Extraction completed successfully![/green]")
                console.print(
                    f"[bold]Questions extracted: {questions_extracted}[/bold]"
                )
                console.print(
                    f"[bold]Discussions extracted: {discussions_extracted}[/bold]"
                )
                console.print(
                    f"[dim]Time taken: {(end_time - start_time).total_seconds():.1f} seconds[/dim]"
                )

                if extraction_errors:
                    console.print(
                        f"[yellow]⚠️  {len(extraction_errors)} errors occurred during extraction[/yellow]"
                    )
            else:
                console.print("[red]❌ Extraction failed[/red]")
                console.print(f"[red]Errors: {len(extraction_errors)}[/red]")

        finally:
            scraper.close()

    except KeyboardInterrupt:
        console.print("\n[yellow]Extraction cancelled by user.[/yellow]")
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def extract_local(
    html_path: str = typer.Argument(
        ...,
        help="Path to an HTML file or folder containing HTML files with exam questions",
    ),
    exam_name: str = typer.Option(
        None, "--name", help="Name for the exam (auto-generated if not provided)"
    ),
    max_questions: int = typer.Option(
        None, "--max-questions", help="Maximum number of questions to extract"
    ),
    extract_discussions: bool = typer.Option(
        True, "--discussions/--no-discussions", help="Extract discussion data"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode"),
) -> None:
    """Extract exam data from local HTML file(s).

    This command can process either:
    - A single HTML file containing exam questions
    - A folder containing multiple HTML files (e.g., page-1.html, page-2.html, etc.)

    When processing multiple files, questions are automatically deduplicated based on question numbers.
    """
    setup_logging(verbose, debug)

    try:
        # Validate path exists
        input_path = Path(html_path)
        if not input_path.exists():
            console.print(f"[red]❌ Path not found: {html_path}[/red]")
            raise typer.Exit(1)

        # Determine if it's a file or folder and collect HTML files
        html_files = []
        if input_path.is_file():
            if input_path.suffix.lower() not in [".html", ".htm"]:
                console.print(f"[red]❌ File is not an HTML file: {html_path}[/red]")
                raise typer.Exit(1)
            html_files = [input_path]
        elif input_path.is_dir():
            # Find all HTML files in the directory
            html_files = list(input_path.glob("*.html")) + list(
                input_path.glob("*.htm")
            )
            if not html_files:
                console.print(
                    f"[red]❌ No HTML files found in directory: {html_path}[/red]"
                )
                raise typer.Exit(1)
            # Sort files to ensure consistent processing order
            html_files.sort()
        else:
            console.print(
                f"[red]❌ Path is neither a file nor a directory: {html_path}[/red]"
            )
            raise typer.Exit(1)

        # Validate authentication for LLM
        auth_valid, auth_error = validate_authentication()
        if not auth_valid:
            console.print(f"[red]❌ Authentication error: {auth_error}[/red]")
            console.print(
                "[dim]Please run 'gcloud auth application-default login' to authenticate.[/dim]"
            )
            raise typer.Exit(1)

        # Generate exam name if not provided
        if not exam_name:
            if input_path.is_file():
                exam_name = input_path.stem.replace(" ", "-").replace("_", "-")
            else:
                exam_name = input_path.name.replace(" ", "-").replace("_", "-")

        console.print(
            f"[bold blue]🔍 Extracting exam from local files: {exam_name}[/bold blue]"
        )
        if len(html_files) == 1:
            console.print(f"[dim]File: {html_files[0]}[/dim]")
        else:
            console.print(f"[dim]Folder: {html_path}[/dim]")
            console.print(f"[dim]Found {len(html_files)} HTML files[/dim]")
        console.print()

        # Initialize components
        parser = QuestionParser()
        storage = StorageManager()

        start_time = datetime.now()
        extraction_errors = []
        questions_extracted = 0
        discussions_extracted = 0

        try:
            # Collect all question cards from all HTML files
            all_question_cards = []
            total_html_size = 0

            for file_num, html_file in enumerate(
                tqdm(html_files, desc="Reading HTML files", unit="file"), 1
            ):
                try:
                    with open(html_file, encoding="utf-8") as f:
                        html_content = f.read()

                    total_html_size += len(html_content)
                    soup = BeautifulSoup(html_content, "html.parser")

                    # Extract question cards from this file
                    question_cards = extract_question_cards_from_soup(soup)

                    # Add source file information to each card for tracking
                    for card in question_cards:
                        card._source_file = str(
                            html_file
                        )  # Add custom attribute for tracking
                        all_question_cards.append(card)

                except Exception as e:
                    error_msg = f"Failed to read file {html_file}: {e}"
                    extraction_errors.append(error_msg)
                    console.print(f"[red]❌ {error_msg}[/red]")
                    continue

            if not all_question_cards:
                console.print(
                    "[yellow]⚠️ No question cards found in any HTML files[/yellow]"
                )
                console.print(
                    "[dim]Make sure the HTML files contain complete exam pages with questions[/dim]"
                )
                raise typer.Exit(1)

            console.print()
            console.print(
                f"[green]✓ Total HTML content loaded: {total_html_size} characters[/green]"
            )
            console.print("[dim]Extracting and deduplicating question cards...[/dim]")

            # Deduplicate all question cards across all files
            unique_cards = deduplicate_question_cards(all_question_cards)
            console.print(
                f"[green]Found {len(unique_cards)} unique question cards across all files[/green]"
            )

            if len(all_question_cards) > len(unique_cards):
                duplicates_removed = len(all_question_cards) - len(unique_cards)
                console.print(
                    f"[yellow]Removed {duplicates_removed} duplicate questions[/yellow]"
                )

            # Process each unique question card
            for card_num, card in enumerate(
                tqdm(unique_cards, desc="Processing questions", unit="question"), 1
            ):
                try:
                    # Use the source file information if available
                    source_file = getattr(card, "_source_file", str(input_path))
                    question = parser.parse_question_card(card, source_file, 1)
                    if question:
                        storage.save_question(question, exam_name)
                        questions_extracted += 1

                        # Extract discussion if enabled
                        if extract_discussions:
                            try:
                                discussion = parser.parse_discussion(card, question.id)
                                if discussion:
                                    storage.save_discussion(discussion, exam_name)
                                    discussions_extracted += 1
                            except Exception as e:
                                if verbose:
                                    console.print(
                                        f"[yellow]⚠️ Failed to extract discussion for question {card_num}: {e}[/yellow]"
                                    )

                        if max_questions and questions_extracted >= max_questions:
                            console.print(
                                f"[yellow]Reached maximum questions limit: {max_questions}[/yellow]"
                            )
                            break
                    elif verbose:
                        console.print(
                            f"[yellow]⚠️ Failed to parse question {card_num}[/yellow]"
                        )

                except Exception as e:
                    error_msg = f"Failed to extract question {card_num}: {e}"
                    extraction_errors.append(error_msg)
                    if verbose:
                        console.print(f"[red]❌ {error_msg}[/red]")

            # Save exam metadata
            source_url = f"file://{input_path.absolute()}"
            if len(html_files) > 1:
                source_url += f" ({len(html_files)} files)"

            exam_info = ExamInfo(
                name=exam_name,
                vendor="ExamTopics",
                code=exam_name,
                total_questions=questions_extracted,
                url=source_url,
                last_updated=datetime.now(),
            )
            storage.save_exam_metadata(exam_info, exam_name)

            # Create extraction report
            end_time = datetime.now()
            report = ExtractionReport(
                exam_info=exam_info,
                questions_extracted=questions_extracted,
                discussions_extracted=discussions_extracted,
                extraction_errors=extraction_errors,
                start_time=start_time,
                end_time=end_time,
                success=questions_extracted > 0,
            )
            storage.save_extraction_report(report, exam_name)

            # Display results
            console.print()
            if report.success:
                console.print("[green]✅ Extraction completed successfully![/green]")
                console.print(
                    f"[bold]Questions extracted: {questions_extracted}[/bold]"
                )
                console.print(
                    f"[bold]Discussions extracted: {discussions_extracted}[/bold]"
                )
                console.print(f"[bold]Files processed: {len(html_files)}[/bold]")
                console.print(
                    f"[dim]Time taken: {(end_time - start_time).total_seconds():.1f} seconds[/dim]"
                )

                if extraction_errors:
                    console.print(
                        f"[yellow]⚠️  {len(extraction_errors)} errors occurred during extraction[/yellow]"
                    )
                    if debug:
                        for error in extraction_errors[:5]:  # Show first 5 errors
                            console.print(f"[dim]  • {error}[/dim]")
                        if len(extraction_errors) > 5:
                            console.print(
                                f"[dim]  ... and {len(extraction_errors) - 5} more[/dim]"
                            )
            else:
                console.print("[red]❌ Extraction failed[/red]")
                console.print(f"[red]Errors: {len(extraction_errors)}[/red]")

        except Exception as e:
            console.print(f"[red]❌ Failed to process HTML files: {e}[/red]")
            if debug:
                console.print_exception()
            raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Extraction cancelled by user.[/yellow]")
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def deduplicate_question_cards(
    question_cards: list[BeautifulSoup],
) -> list[BeautifulSoup]:
    """Deduplicate question cards based on question numbers across multiple files.

    Args:
        question_cards: List of BeautifulSoup objects for question cards

    Returns:
        List of unique BeautifulSoup objects for question cards
    """
    unique_cards = []
    seen_question_numbers = set()

    for card in question_cards:
        # Extract question number from the card
        card_text = card.get_text()
        question_number = None

        # Look for question number patterns
        patterns = [
            r"Question #(\d+)",
            r"Question (\d+)",
            r"Q(\d+)",
            r"#(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, card_text)
            if match:
                question_number = int(match.group(1))
                break

        # Only add if we haven't seen this question number before
        if question_number and question_number not in seen_question_numbers:
            seen_question_numbers.add(question_number)
            unique_cards.append(card)
        elif question_number is None:
            # If we can't extract a question number, include it anyway
            # (but this shouldn't happen with proper question cards)
            unique_cards.append(card)

    return unique_cards


def extract_question_cards_from_soup(soup: BeautifulSoup) -> list[BeautifulSoup]:
    """Extract question cards from BeautifulSoup object using the same logic as scraper.

    Args:
        soup: BeautifulSoup object of the HTML content

    Returns:
        List of BeautifulSoup objects for each question card (deduplicated)
    """

    # More specific selectors for question cards on ExamTopics
    question_selectors = [
        "div.exam-question-card",  # Most specific for ExamTopics
        "div.card.exam-question-card",  # Alternative specific selector
        "div.question-card",
        "div.card.question",
        "div.exam-question",
        "article.question",
        "div.question-container",
        "div.question-wrapper",
    ]

    question_cards = []
    for selector in question_selectors:
        cards = soup.select(selector)
        if cards:
            question_cards.extend(cards)
            break

    # Fallback: look for cards with question numbers or patterns
    if not question_cards:
        # Look for divs containing "Question" text
        all_divs = soup.find_all("div")
        for div in all_divs:
            text = div.get_text(strip=True)
            # Check for question patterns - be more specific
            if text.startswith("Question #") and (
                "Topic" in text or "Question #" in text[:20]
            ):  # More specific pattern
                question_cards.append(div)

    # Alternative approach: look for numbered patterns
    if not question_cards:
        # Look for elements with question numbering patterns
        numbered_elements = soup.find_all(
            ["div", "section", "article"],
            string=lambda text: text
            and any(
                pattern in text
                for pattern in [
                    "Question 1",
                    "Question 2",
                    "Question 3",
                    "Q1.",
                    "Q2.",
                    "Q3.",
                    "1.",
                    "2.",
                    "3.",
                ]
            ),
        )
        if numbered_elements:
            # Find parent containers that likely contain the full question
            for elem in numbered_elements:
                parent = elem.find_parent(["div", "section", "article"])
                if parent and parent not in question_cards:
                    question_cards.append(parent)

    # Deduplicate question cards based on question numbers
    unique_cards = deduplicate_question_cards(question_cards)

    return unique_cards


@app.command()
def list_exams() -> None:
    """List available exams in storage."""
    try:
        storage = StorageManager()
        exams = storage.list_available_exams()

        if not exams:
            console.print("[yellow]No exams found in storage.[/yellow]")
            console.print("[dim]Use 'extract' command to download exam data.[/dim]")
            return

        console.print("[bold]📚 Available Exams:[/bold]")
        console.print()

        for exam_name in exams:
            stats = storage.get_exam_stats(exam_name)
            metadata = storage.load_exam_metadata(exam_name)

            console.print(f"[cyan]• {exam_name}[/cyan]")
            console.print(f"  Questions: {stats.get('questions', 0)}")
            console.print(f"  Discussions: {stats.get('discussions', 0)}")

            if metadata:
                console.print(
                    f"  Last updated: {metadata.last_updated.strftime('%Y-%m-%d %H:%M')}"
                )
                console.print(f"  Source: {metadata.url}")

            console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    exam_name: str = typer.Argument(..., help="Name of the exam to validate"),
) -> None:
    """Validate exam data integrity."""
    try:
        storage = StorageManager()
        results = storage.validate_data_integrity(exam_name)

        console.print(f"[bold]🔍 Validating exam: {exam_name}[/bold]")
        console.print()

        # Display validation results
        console.print(
            f"[green]✅ Valid questions: {len(results['valid_questions'])}[/green]"
        )
        console.print(
            f"[green]✅ Valid discussions: {len(results['valid_discussions'])}[/green]"
        )

        if results["invalid_questions"]:
            console.print(
                f"[red]❌ Invalid questions: {len(results['invalid_questions'])}[/red]"
            )
            for error in results["invalid_questions"]:
                console.print(f"  [red]• {error}[/red]")

        if results["invalid_discussions"]:
            console.print(
                f"[red]❌ Invalid discussions: {len(results['invalid_discussions'])}[/red]"
            )
            for error in results["invalid_discussions"]:
                console.print(f"  [red]• {error}[/red]")

        if results["errors"]:
            console.print(f"[red]❌ General errors: {len(results['errors'])}[/red]")
            for error in results["errors"]:
                console.print(f"  [red]• {error}[/red]")

        total_issues = (
            len(results["invalid_questions"])
            + len(results["invalid_discussions"])
            + len(results["errors"])
        )
        if total_issues == 0:
            console.print("\n[green]🎉 All data is valid![/green]")
        else:
            console.print(f"\n[yellow]⚠️  Found {total_issues} issues[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"cert-examtopics-quiz version {__version__}")


def setup_logging(verbose: bool, debug: bool) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def cli() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    cli()
