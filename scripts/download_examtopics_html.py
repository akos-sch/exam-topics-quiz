#!/usr/bin/env python3
"""
Helper script to download HTML files from ExamTopics for local processing.

This script helps users manually download ExamTopics pages to bypass captcha
and authentication issues. The downloaded HTML files can then be processed
using the 'extract-local' command.

Usage:
    python scripts/download_examtopics_html.py <exam_url> [output_file]

Example:
    python scripts/download_examtopics_html.py \
        "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/view/2/" \
        exam_page.html
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def download_examtopics_page(url: str, output_file: str = None) -> str:
    """Download an ExamTopics page and save it as HTML.

    Args:
        url: ExamTopics URL to download
        output_file: Output filename (auto-generated if None)

    Returns:
        Path to the saved HTML file
    """
    # Generate output filename if not provided
    if not output_file:
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2:
            output_file = f"{path_parts[-2]}_{path_parts[-1]}.html"
        else:
            output_file = "examtopics_page.html"

    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"📥 Downloading: {url}")
    print(f"💾 Output file: {output_file}")
    print()

    # Setup session with browser-like headers
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    try:
        # Download the page
        response = session.get(url, timeout=30)
        response.raise_for_status()

        # Parse and check content
        soup = BeautifulSoup(response.content, "html.parser")
        page_title = soup.title.string if soup.title else "Unknown"

        print("✅ Page downloaded successfully")
        print(f"📄 Title: {page_title}")
        print(f"📊 Size: {len(response.content)} bytes")

        # Check for common issues
        page_text = soup.get_text().lower()
        if "captcha" in page_text or "i am not a robot" in page_text:
            print(
                "⚠️  WARNING: Page contains captcha - you may need to solve it manually"
            )
            print(
                "   Try opening the URL in a browser, solve the captcha, then save the page"
            )

        if "login" in page_text and "password" in page_text:
            print("⚠️  WARNING: Page appears to require login")
            print(
                "   You may need to log in first and then save the authenticated page"
            )

        # Look for question indicators
        question_indicators = [
            "question #",
            "question ",
            "q1.",
            "q2.",
            "q3.",
            "multiple choice",
            "select the",
            "choose the",
        ]

        has_questions = any(indicator in page_text for indicator in question_indicators)
        if has_questions:
            print("✅ Page appears to contain questions")
        else:
            print("⚠️  WARNING: Page may not contain questions")
            print("   Make sure you're downloading the correct exam page")

        # Save the HTML file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        print(f"\n💾 HTML file saved: {output_path.absolute()}")
        print("\n🚀 Next steps:")
        print("   1. Review the downloaded HTML file to ensure it contains questions")
        print(f'   2. Run: uv run cert-examtopics-quiz extract-local "{output_file}"')

        return str(output_path)

    except requests.RequestException as e:
        print(f"❌ Failed to download page: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    """Main function for the download script."""
    parser = argparse.ArgumentParser(
        description="Download ExamTopics HTML files for local processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download with auto-generated filename
  python scripts/download_examtopics_html.py "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/view/2/"

  # Download with custom filename
  python scripts/download_examtopics_html.py "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/view/2/" ml_engineer_exam.html

  # Then extract questions
  uv run cert-examtopics-quiz extract-local ml_engineer_exam.html --name "ML-Engineer-Exam"
        """,
    )

    parser.add_argument("url", help="ExamTopics URL to download")

    parser.add_argument(
        "output_file",
        nargs="?",
        help="Output HTML filename (auto-generated if not provided)",
    )

    args = parser.parse_args()

    # Validate URL
    if not args.url.startswith("http"):
        print("❌ Error: URL must start with http:// or https://")
        sys.exit(1)

    if "examtopics.com" not in args.url:
        print("⚠️  WARNING: URL doesn't appear to be from ExamTopics")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            sys.exit(0)

    # Download the page
    download_examtopics_page(args.url, args.output_file)


if __name__ == "__main__":
    main()
