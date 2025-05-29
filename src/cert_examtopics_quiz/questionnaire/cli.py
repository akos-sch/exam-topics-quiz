"""CLI interface for interactive quiz taking."""

import logging
import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from ..config.settings import get_settings
from ..models.session import QuizSettings
from .engine import QuizEngine
from .loader import DataLoader

logger = logging.getLogger(__name__)


class CLIInterface:
    """Command-line interface for taking quizzes."""

    def __init__(self):
        """Initialize the CLI interface."""
        self.console = Console()
        self.settings = get_settings()
        self.data_loader = DataLoader()
        self.quiz_engine = QuizEngine()

    def clear_screen(self) -> None:
        """Clear the terminal screen if enabled."""
        if self.settings.display.clear_screen:
            os.system("cls" if os.name == "nt" else "clear")

    def display_welcome(self) -> None:
        """Display welcome message."""
        self.console.print(
            Panel.fit(
                "[bold blue]🎓 Certificate ExamTopics Quiz[/bold blue]\n"
                "[dim]Interactive quiz application for exam preparation[/dim]",
                border_style="blue",
            )
        )
        self.console.print()

    def select_exam(self) -> str | None:
        """Let user select an exam from available options.

        Returns:
            Selected exam name or None if cancelled
        """
        available_exams = self.data_loader.get_available_exams()

        if not available_exams:
            self.console.print("[red]❌ No exams found in storage.[/red]")
            self.console.print(
                "[dim]Please run the extractor first to download exam data.[/dim]"
            )
            return None

        self.console.print("[bold]📚 Available Exams:[/bold]")

        # Display exam options with statistics
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Index", style="dim", width=6)
        table.add_column("Exam Name", style="cyan")
        table.add_column("Questions", justify="right", style="green")
        table.add_column("Discussions", justify="right", style="yellow")

        for i, exam_name in enumerate(available_exams, 1):
            stats = self.data_loader.get_exam_stats(exam_name)
            table.add_row(
                str(i),
                exam_name,
                str(stats.get("questions", 0)),
                str(stats.get("discussions", 0)),
            )

        self.console.print(table)
        self.console.print()

        # Get user selection
        try:
            choice = IntPrompt.ask(
                "Select exam",
                choices=[str(i) for i in range(1, len(available_exams) + 1)],
                show_choices=False,
            )
            return available_exams[choice - 1]
        except (KeyboardInterrupt, EOFError):
            return None

    def configure_quiz(self, exam_name: str) -> QuizSettings | None:
        """Configure quiz settings.

        Args:
            exam_name: Name of the selected exam

        Returns:
            QuizSettings object or None if cancelled
        """
        self.console.print(
            f"[bold]⚙️  Configuring quiz for: [cyan]{exam_name}[/cyan][/bold]"
        )
        self.console.print()

        # Get total available questions
        questions = self.data_loader.load_questions(exam_name)
        total_questions = len(questions)

        if total_questions == 0:
            self.console.print("[red]❌ No questions found for this exam.[/red]")
            return None

        self.console.print(f"[dim]Total questions available: {total_questions}[/dim]")
        self.console.print()

        try:
            # Number of questions
            default_count = min(
                self.settings.quiz.default_question_count, total_questions
            )
            question_count = IntPrompt.ask(
                "Number of questions", default=default_count, show_default=True
            )
            question_count = min(question_count, total_questions)

            # Time limit
            time_limit = None
            if Confirm.ask("Set time limit?", default=False):
                time_limit = (
                    IntPrompt.ask(
                        "Time limit (minutes)",
                        default=self.settings.quiz.time_limit // 60,
                    )
                    * 60
                )

            # Randomization options
            randomize_questions = Confirm.ask(
                "Randomize question order?",
                default=self.settings.quiz.randomize_questions,
            )

            randomize_choices = Confirm.ask(
                "Randomize choice order?", default=self.settings.quiz.randomize_choices
            )

            # Show explanations
            show_explanations = Confirm.ask(
                "Show explanations after each question?",
                default=self.settings.quiz.show_explanations,
            )

            # Show immediate feedback
            show_immediate_feedback = Confirm.ask(
                "Show correct/incorrect answer immediately?",
                default=self.settings.quiz.show_immediate_feedback,
            )

            # Show community votes
            show_community_votes = Confirm.ask(
                "Show community voting data?",
                default=self.settings.quiz.show_community_votes,
            )

            return QuizSettings(
                question_count=question_count,
                time_limit=time_limit,
                randomize_questions=randomize_questions,
                randomize_choices=randomize_choices,
                show_explanations=show_explanations,
                show_immediate_feedback=show_immediate_feedback,
                show_community_votes=show_community_votes,
            )

        except (KeyboardInterrupt, EOFError):
            return None

    def start_quiz(self, exam_name: str, settings: QuizSettings) -> None:
        """Start and run the quiz.

        Args:
            exam_name: Name of the exam
            settings: Quiz configuration settings
        """
        # Load questions
        self.console.print("[dim]Loading questions...[/dim]")
        questions = self.data_loader.load_questions(exam_name)

        if not questions:
            self.console.print("[red]❌ Failed to load questions.[/red]")
            return

        # Create quiz session
        session = self.quiz_engine.create_session(exam_name, questions, settings)

        self.console.print(
            f"[green]✅ Quiz started with {len(session.questions)} questions[/green]"
        )

        if settings.time_limit:
            minutes = settings.time_limit // 60
            self.console.print(f"[yellow]⏰ Time limit: {minutes} minutes[/yellow]")

        self.console.print()

        # Main quiz loop
        while not self.quiz_engine.is_quiz_complete():
            if self.quiz_engine.is_time_expired():
                self.console.print("[red]⏰ Time expired![/red]")
                break

            self.display_question()

            if not self.handle_question_input():
                break  # User quit

        # Finish quiz and show results
        self.finish_quiz()

    def display_question(self) -> None:
        """Display the current question."""
        if self.settings.display.clear_screen:
            self.clear_screen()

        question = self.quiz_engine.get_current_question()
        if not question:
            return

        progress = self.quiz_engine.get_progress()

        # Display progress header
        progress_text = (
            f"Question {progress['current_question']}/{progress['total_questions']}"
        )
        if self.settings.display.show_timer:
            elapsed_minutes = int(progress["elapsed_time"] // 60)
            elapsed_seconds = int(progress["elapsed_time"] % 60)
            progress_text += f" | Time: {elapsed_minutes:02d}:{elapsed_seconds:02d}"

            # Show remaining time if there's a limit
            remaining = self.quiz_engine.get_time_remaining()
            if remaining is not None:
                remaining_minutes = int(remaining // 60)
                remaining_seconds = int(remaining % 60)
                progress_text += (
                    f" | Remaining: {remaining_minutes:02d}:{remaining_seconds:02d}"
                )

        self.console.print(Panel(progress_text, style="bold blue"))
        self.console.print()

        # Display question
        question_panel = Panel(
            f"[bold]{question.text}[/bold]",
            title=f"[cyan]Question #{question.number}[/cyan]",
            title_align="left",
            border_style="cyan",
        )
        self.console.print(question_panel)
        self.console.print()

        # Display choices
        choice_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]  # Standard letters
        for i, choice in enumerate(question.choices):
            choice_style = "white"
            if (
                choice.is_most_voted
                and self.quiz_engine.current_session is not None
                and self.quiz_engine.current_session.settings.show_community_votes
            ):
                choice_style = "yellow"

            # Use sequential letters (A, B, C, D) instead of original randomized letters
            display_letter = (
                choice_letters[i] if i < len(choice_letters) else str(i + 1)
            )

            # Add vote info if community votes are enabled
            vote_info = ""
            if (
                self.quiz_engine.current_session is not None
                and self.quiz_engine.current_session.settings.show_community_votes
                and question.voting_data.total_votes > 0
            ):
                if question.voting_data.vote_distribution:
                    # We have detailed vote breakdown
                    vote_count = question.voting_data.vote_distribution.get(
                        choice.letter, 0
                    )
                    total_votes = question.voting_data.total_votes
                    percentage = (
                        (vote_count / total_votes * 100) if total_votes > 0 else 0
                    )
                    vote_info = f" [{vote_count} votes, {percentage:.1f}%]"
                elif choice.letter == question.voting_data.most_voted_answer:
                    # We only know which choice got the most votes
                    vote_info = " [Most voted]"

            self.console.print(
                f"[{choice_style}]{display_letter}. {choice.text}{vote_info}[/{choice_style}]"
            )

        self.console.print()

        # Show voting info if available and enabled
        if (
            question.voting_data.total_votes > 0
            and self.quiz_engine.current_session is not None
            and self.quiz_engine.current_session.settings.show_community_votes
        ):
            # Find the display letter for the most voted choice
            most_voted_display_letter = (
                question.voting_data.most_voted_answer
            )  # Default fallback
            choice_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for i, choice in enumerate(question.choices):
                if choice.letter == question.voting_data.most_voted_answer:
                    most_voted_display_letter = (
                        choice_letters[i] if i < len(choice_letters) else str(i + 1)
                    )
                    break

            votes_text = f"Community votes: {question.voting_data.total_votes} "
            votes_text += f"(Most voted: {most_voted_display_letter})"
            self.console.print(f"[dim]{votes_text}[/dim]")
            self.console.print()

    def handle_question_input(self) -> bool:
        """Handle user input for the current question.

        Returns:
            True to continue, False to quit
        """
        question = self.quiz_engine.get_current_question()
        if not question:
            return False

        # Create mapping from display letters to original choice letters
        choice_mapping = {}
        valid_display_choices = []
        choice_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]

        for i, choice in enumerate(question.choices):
            display_letter = (
                choice_letters[i] if i < len(choice_letters) else str(i + 1)
            )
            choice_mapping[display_letter] = choice.letter
            valid_display_choices.append(display_letter)

        valid_choices = valid_display_choices + ["S", "Q"]  # Skip and quit options

        prompt_text = (
            f"Your answer ([{'/'.join(valid_display_choices)}], [S]kip, [Q]uit)"
        )

        try:
            answer = Prompt.ask(
                prompt_text, choices=valid_choices, show_choices=False
            ).upper()

            if answer == "Q":
                return False
            elif answer == "S":
                self.quiz_engine.skip_question()
                self.console.print("[yellow]⏭️  Question skipped[/yellow]")
            else:
                # Convert display letter back to original choice letter
                original_choice = choice_mapping[answer]
                self.quiz_engine.submit_answer(original_choice)

                # Show immediate feedback if enabled
                if (
                    self.quiz_engine.current_session is not None
                    and self.quiz_engine.current_session.settings.show_immediate_feedback
                ):
                    current_question = question  # Store before moving to next
                    is_correct = original_choice == current_question.correct_answer

                    if is_correct:
                        self.console.print("[green]✅ Correct![/green]")
                    else:
                        self.console.print(
                            f"[red]❌ Incorrect. Correct answer: {current_question.correct_answer}[/red]"
                        )

                    # Show explanation if enabled and available
                    if (
                        self.quiz_engine.current_session is not None
                        and self.quiz_engine.current_session.settings.show_explanations
                        and current_question.explanation
                    ):
                        explanation_panel = Panel(
                            current_question.explanation,
                            title="[yellow]Explanation[/yellow]",
                            border_style="yellow",
                        )
                        self.console.print()
                        self.console.print(explanation_panel)

            # Pause before next question
            if not self.quiz_engine.is_quiz_complete():
                self.console.print()
                self.console.print("[dim]Press Enter to continue...[/dim]")
                input()

            return True

        except (KeyboardInterrupt, EOFError):
            return False

    def finish_quiz(self) -> None:
        """Finish the quiz and display results."""
        result = self.quiz_engine.finish_quiz()

        if not result:
            self.console.print("[red]❌ Failed to calculate results.[/red]")
            return

        self.clear_screen()

        # Display results header
        score_color = (
            "green"
            if result.score_percentage >= 70
            else "yellow"
            if result.score_percentage >= 50
            else "red"
        )

        results_panel = Panel(
            f"[bold {score_color}]Quiz Complete![/bold {score_color}]\n\n"
            f"[bold]Score: {result.correct_answers}/{result.total_questions} ({result.score_percentage:.1f}%)[/bold]\n"
            f"Time taken: {self.format_time(result.total_time)}\n"
            f"Average per question: {self.format_time(result.average_time_per_question)}",
            title="[cyan]📊 Results[/cyan]",
            border_style=score_color,
        )
        self.console.print(results_panel)
        self.console.print()

        # Show detailed results if requested
        if Confirm.ask("Show detailed results?", default=True):
            self.display_detailed_results()

    def display_detailed_results(self) -> None:
        """Display detailed quiz results."""
        detailed = self.quiz_engine.get_detailed_results()

        if not detailed:
            return

        # Topic performance
        if detailed["topic_performance"]:
            self.console.print("[bold]📈 Performance by Topic:[/bold]")

            topic_table = Table(show_header=True, header_style="bold magenta")
            topic_table.add_column("Topic", style="cyan")
            topic_table.add_column("Correct", justify="right", style="green")
            topic_table.add_column("Total", justify="right")
            topic_table.add_column("Percentage", justify="right", style="yellow")

            for topic, stats in detailed["topic_performance"].items():
                percentage_color = (
                    "green"
                    if stats["percentage"] >= 70
                    else "yellow"
                    if stats["percentage"] >= 50
                    else "red"
                )
                topic_table.add_row(
                    topic,
                    str(stats["correct"]),
                    str(stats["total"]),
                    f"[{percentage_color}]{stats['percentage']:.1f}%[/{percentage_color}]",
                )

            self.console.print(topic_table)
            self.console.print()

        # Time statistics
        time_stats = detailed["time_statistics"]
        self.console.print("[bold]⏱️  Time Statistics:[/bold]")
        self.console.print(
            f"Fastest question: {self.format_time(time_stats['fastest_question'])}"
        )
        self.console.print(
            f"Slowest question: {self.format_time(time_stats['slowest_question'])}"
        )
        self.console.print(
            f"Median time: {self.format_time(time_stats['median_time'])}"
        )
        self.console.print()

        # Question-by-question review
        if Confirm.ask("Review incorrect answers?", default=True):
            self.review_incorrect_answers(detailed["question_results"])

    def review_incorrect_answers(self, question_results: list[dict]) -> None:
        """Review incorrect answers in detail.

        Args:
            question_results: List of question result dictionaries
        """
        incorrect_results = [r for r in question_results if not r["is_correct"]]

        if not incorrect_results:
            self.console.print("[green]🎉 All answers were correct![/green]")
            return

        self.console.print(
            f"[bold]📝 Reviewing {len(incorrect_results)} incorrect answers:[/bold]"
        )
        self.console.print()

        for i, result in enumerate(incorrect_results, 1):
            question = result["question"]
            user_answer = result["user_answer"]

            self.console.print(f"[bold cyan]Question #{question.number}:[/bold cyan]")
            self.console.print(question.text)
            self.console.print()

            # Show choices with user's answer and correct answer highlighted
            choice_letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
            for j, choice in enumerate(question.choices):
                display_letter = (
                    choice_letters[j] if j < len(choice_letters) else str(j + 1)
                )
                style = "white"
                prefix = " "

                if choice.letter == user_answer.selected_choice:
                    style = "red"
                    prefix = "❌"
                elif choice.letter == question.correct_answer:
                    style = "green"
                    prefix = "✅"

                # Get vote count and percentage for this choice
                vote_count = question.voting_data.vote_distribution.get(
                    choice.letter, 0
                )
                total_votes = question.voting_data.total_votes
                percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0

                # Format vote info - handle case where detailed distribution isn't available
                vote_info = ""
                if total_votes > 0:
                    if question.voting_data.vote_distribution:
                        # We have detailed vote breakdown
                        vote_info = f" [{vote_count} votes, {percentage:.1f}%]"
                    elif (
                        choice.letter == question.voting_data.most_voted_answer
                        and question.voting_data.confidence_score > 0.0
                    ):
                        # Calculate vote count from confidence score for most voted answer
                        most_voted_count = round(
                            total_votes * question.voting_data.confidence_score
                        )
                        vote_info = f" [Most voted - {most_voted_count} votes]"
                    elif choice.letter == question.voting_data.most_voted_answer:
                        # We only know which choice got the most votes (confidence is 0)
                        vote_info = f" [Most voted - {total_votes} total votes]"
                    elif choice.letter == question.correct_answer:
                        # Show total votes for correct answer if it's not the most voted
                        vote_info = " [Correct answer]"

                self.console.print(
                    f"[{style}]{prefix} {display_letter}. {choice.text}{vote_info}[/{style}]"
                )

            self.console.print()

            # Show detailed community voting summary
            if question.voting_data.total_votes > 0:
                # Find the display letter for the most voted choice
                most_voted_display_letter = (
                    question.voting_data.most_voted_answer
                )  # Default fallback
                for j, choice in enumerate(question.choices):
                    if choice.letter == question.voting_data.most_voted_answer:
                        most_voted_display_letter = (
                            choice_letters[j] if j < len(choice_letters) else str(j + 1)
                        )
                        break

                if question.voting_data.vote_distribution:
                    # Full detailed voting summary
                    most_voted_count = question.voting_data.vote_distribution.get(
                        question.voting_data.most_voted_answer, 0
                    )
                    voting_summary = (
                        f"[bold]Community Voting Summary[/bold]\n"
                        f"Total votes: {question.voting_data.total_votes}\n"
                        f"Most voted: {most_voted_display_letter} ({most_voted_count} votes)\n"
                        f"Confidence score: {question.voting_data.confidence_score:.2f}"
                    )
                # Limited voting summary - calculate most voted count from confidence score
                elif question.voting_data.confidence_score > 0.0:
                    most_voted_count = round(
                        question.voting_data.total_votes
                        * question.voting_data.confidence_score
                    )
                    voting_summary = (
                        f"[bold]Community Voting Summary[/bold]\n"
                        f"Total votes: {question.voting_data.total_votes}\n"
                        f"Most voted: {most_voted_display_letter} ({most_voted_count} votes)\n"
                        f"Confidence score: {question.voting_data.confidence_score:.2f}\n"
                        f"[dim]Note: Vote count estimated from confidence score[/dim]"
                    )
                else:
                    voting_summary = (
                        f"[bold]Community Voting Summary[/bold]\n"
                        f"Total votes: {question.voting_data.total_votes}\n"
                        f"Most voted: {most_voted_display_letter}\n"
                        f"Confidence score: {question.voting_data.confidence_score:.2f}\n"
                        f"[dim]Note: Detailed vote breakdown not available[/dim]"
                    )

                voting_panel = Panel(
                    voting_summary,
                    title="[blue]📊 Community Data[/blue]",
                    border_style="blue",
                )
                self.console.print(voting_panel)
                self.console.print()

            if result["explanation"]:
                explanation_panel = Panel(
                    result["explanation"],
                    title="[yellow]Explanation[/yellow]",
                    border_style="yellow",
                )
                self.console.print(explanation_panel)

            # Add separator line between questions (except for the last one)
            if i < len(incorrect_results):
                self.console.print()
                self.console.print("─" * 80)  # White separator line
                self.console.print()

    def format_time(self, seconds: float) -> str:
        """Format time in a human-readable format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"

        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"

    def run(self) -> None:
        """Run the main CLI interface."""
        try:
            self.display_welcome()

            # Select exam
            exam_name = self.select_exam()
            if not exam_name:
                return

            # Configure quiz
            settings = self.configure_quiz(exam_name)
            if not settings:
                return

            # Start quiz
            self.start_quiz(exam_name, settings)

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Quiz interrupted by user.[/yellow]")
        except Exception as e:
            logger.error(f"CLI error: {e}")
            self.console.print(f"[red]❌ An error occurred: {e}[/red]")
        finally:
            self.console.print(
                "\n[dim]Thank you for using Certificate ExamTopics Quiz![/dim]"
            )
