"""Tests for the main module."""

import contextlib

from cert_examtopics_quiz.main import main


def test_main_runs_without_error():
    """Test that main function runs without raising an exception."""
    # This is a basic smoke test
    with contextlib.suppress(SystemExit):
        main()


def test_main_function_exists():
    """Test that main function is callable."""
    assert callable(main)
