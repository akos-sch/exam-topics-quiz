# Certificate ExamTopics Quiz

A comprehensive quiz application for certificate exam preparation that extracts questions from ExamTopics and provides an interactive quiz interface.

## Features

- **Web Scraping**: Extract exam questions from ExamTopics website with rate limiting and ethical scraping practices
- **LLM-Powered Extraction**: Uses Google's Gemini models via LangChain for intelligent data extraction from HTML
- **Interactive Quiz Interface**: Rich CLI interface with progress tracking, timing, and detailed results
- **Flexible Configuration**: Customizable quiz settings, extraction parameters, and display options
- **Data Validation**: Comprehensive data integrity checks and validation
- **Multiple Interfaces**: CLI interface with plans for web and GUI interfaces

## Installation

### Prerequisites

1. **Python 3.12+**: The application requires Python 3.12 or later
2. **uv**: Fast Python package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))
3. **Google Cloud Project**: For LLM-powered extraction (optional, falls back to traditional parsing)
4. **Google Cloud Authentication**: Set up Application Default Credentials

### Why uv?

This project uses `uv` for package management because it provides:
- **Speed**: 10-100x faster than pip for dependency resolution and installation
- **Reliability**: Deterministic dependency resolution with lock files
- **Simplicity**: Automatic virtual environment management
- **Compatibility**: Drop-in replacement for pip with better performance

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd cert-examtopics-quiz
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

   > **Note**: `uv` automatically creates and manages a virtual environment in `.venv/`. You can use `uv run` to execute commands within this environment without manual activation.

3. **Activate the virtual environment** (if not using `uv run`):
   ```bash
   source .venv/bin/activate  # On Unix/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

4. **Set up Google Cloud authentication** (optional but recommended):
   ```bash
   # Install Google Cloud CLI if not already installed
   # https://cloud.google.com/sdk/docs/install

   # Authenticate with Google Cloud
   gcloud auth application-default login

   # Set your project (optional)
   gcloud config set project YOUR_PROJECT_ID
   ```

5. **Enable Vertex AI API** (if using Google Cloud):
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

## Usage

The application provides several commands for different operations:

### 1. Take a Quiz

Start an interactive quiz session:

```bash
# Start quiz with default settings
uv run cert-examtopics-quiz quiz

# Start quiz with verbose output
uv run cert-examtopics-quiz quiz --verbose
```

The quiz interface will guide you through:
- Selecting an available exam
- Configuring quiz settings (number of questions, time limits, etc.)
- Taking the quiz with real-time feedback
- Reviewing detailed results and performance analysis


### 2. Extract Exam Data (in case you want to extract new exams)

The application provides two main extraction methods to handle different scenarios:

#### Option A: Local HTML File Extraction (Recommended) - Not needed if the `data/exams/gcp-ml-engineer-full` folder exists and is loaded

If you encounter captcha, authentication issues, or want offline processing, you can manually download HTML files and extract from them:

**Step 1: Download HTML file(s)**

```bash
# Option 1: Manual browser download
# 1. Open the exam URL in your browser
# 2. Solve any captcha if present (important!)
# 3. Log in if you have premium access (optional but recommended)
# 4. Save the complete webpage (Ctrl+S or Cmd+S)
# 5. Choose "Webpage, Complete" or "HTML Only"
```

**Step 2: Extract from local file(s)**

```bash
# Extract from a single HTML file
uv run cert-examtopics-quiz extract-local ml_engineer_exam.html --name "gcp-ml-engineer"

# Extract from multiple HTML files in a folder
uv run cert-examtopics-quiz extract-local exam_pages/ --name "my-exam"

# Extract with options and limits
uv run cert-examtopics-quiz extract-local \
  exam_page.html \
  --name "my-exam" \
  --max-questions 50 \
  --no-discussions \
  --verbose \
  --debug
```

**Advanced Features of Local Extraction:**
- 📁 **Folder processing**: Automatically processes multiple HTML files (e.g., page-1.html, page-2.html)
- 🔄 **Automatic deduplication**: Removes duplicate questions across multiple files
- 📊 **Question numbering**: Intelligently extracts and validates question numbers
- 🎯 **Smart parsing**: Uses multiple CSS selectors to find question cards
- ✅ **Validation**: Checks for question patterns and content quality

**Benefits of Local Extraction:**
- ✅ Bypasses captcha and authentication issues
- ✅ Works with premium ExamTopics content
- ✅ Faster processing (no network delays)
- ✅ Can be repeated without re-downloading
- ✅ Works offline after initial download
- ✅ Supports batch processing of multiple pages
- ✅ Automatic deduplication across files

#### Option B: Direct Web Extraction

Extract questions directly from ExamTopics website:

```bash
# Extract from a specific exam URL (basic usage)
uv run cert-examtopics-quiz extract "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/"

# Extract with custom name and limits
uv run cert-examtopics-quiz extract \
  "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/" \
  --name "gcp-ml-engineer" \
  --max-questions 50 \
  --verbose

# Extract with authentication (for premium content)
uv run cert-examtopics-quiz extract \
  "https://www.examtopics.com/exams/aws/aws-certified-solutions-architect-associate/" \
  --username "your-email@example.com" \
  --password "your-password" \
  --no-discussions

# Extract with debug mode for troubleshooting
uv run cert-examtopics-quiz extract \
  "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/" \
  --debug
```

**Requirements for Web Extraction:**
- ✅ Google Cloud authentication (for LLM processing)
- ⚠️ May encounter captcha or rate limiting
- ⚠️ Requires stable internet connection
- ⚠️ May need ExamTopics account for premium content


### 3. List Available Exams

View all extracted exams:

```bash
uv run cert-examtopics-quiz list-exams
```

### 4. Validate Data

Check data integrity for an exam:

```bash
uv run cert-examtopics-quiz validate "gcp-ml-engineer"
```

### 5. Version Information

```bash
uv run cert-examtopics-quiz version
```

## Configuration

The application uses YAML configuration files and environment variables:

### Configuration Files

- `config/extractor.yaml`: Extraction and scraping settings
- `config/questionnaire.yaml`: Quiz interface settings

### Environment Variables

- `GOOGLE_CLOUD_PROJECT`: GCP project ID (optional)
- `GOOGLE_CLOUD_REGION`: GCP region (default: us-central1)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key (optional)
- `CERT_QUIZ_*`: Any setting can be overridden with environment variables

### Example Configuration

```yaml
# config/extractor.yaml
scraping:
  rate_limit: 1.0
  max_retries: 3
  timeout: 30

llm:
  model: "gemini-2.0-flash-001"
  temperature: 0
  max_tokens: 4000
  rate_limit: 60

extraction:
  use_structured_output: true
  batch_size: 5
  cache_llm_responses: true
```

## Data Storage

The application stores data in a structured format:

```
data/
├── exams/
│   └── exam-name/
│       ├── metadata.json
│       ├── questions/
│       │   ├── question_001.json
│       │   ├── question_002.json
│       │   └── ...
│       ├── discussions/
│       │   ├── question_001_discussion.json
│       │   └── ...
│       └── extraction_report.json
└── cache/
    └── ...
```

## Architecture

The application follows a modular architecture:

- **Extractor Module**: Web scraping, HTML parsing, and data extraction
- **Questionnaire Module**: Quiz interfaces, session management, and scoring
- **Models**: Pydantic data models for type safety and validation
- **Configuration**: Settings management and environment configuration
- **Utils**: Authentication, prompts, and utility functions

### Key Components

1. **ExamTopicsScraper**: Handles web scraping with rate limiting
2. **QuestionParser**: LLM-powered HTML parsing using LangChain
3. **StorageManager**: Data persistence and organization
4. **QuizEngine**: Quiz session management and scoring
5. **CLIInterface**: Rich terminal interface for quizzes

## LLM Integration

The application uses Google's Gemini models through LangChain for intelligent data extraction:

- **Structured Output**: Automatic conversion of HTML to Pydantic models
- **Few-Shot Learning**: Examples provided for better extraction accuracy
- **Fallback Parsing**: Traditional parsing when LLM extraction fails
- **Rate Limiting**: Respects API limits and implements backoff strategies

## Development

### Project Structure

```
src/cert_examtopics_quiz/
├── models/           # Pydantic data models
├── extractor/        # Web scraping and parsing
├── questionnaire/    # Quiz interfaces and engine
├── config/          # Configuration management
├── utils/           # Utilities and helpers
├── cli.py           # Command-line interface
└── main.py          # Main application entry point
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=cert_examtopics_quiz

# Run specific test categories
uv run pytest -m "not slow"  # Skip slow tests
uv run pytest -m integration  # Run only integration tests

# Install and run with test dependencies
uv sync --extra test
uv run pytest
```

### Code Quality

The project uses several tools for code quality:

```bash
# Install development dependencies
uv sync --extra dev

# Format code
uv run ruff format

# Lint code
uv run ruff check

# Type checking
uv run mypy src/

# Pre-commit hooks
uv run pre-commit run --all-files

# Run all quality checks
uv run ruff check && uv run ruff format --check && uv run mypy src/
```

## Ethical Considerations

This application is designed for educational purposes and follows ethical scraping practices:

- **Rate Limiting**: Implements delays between requests to avoid overloading servers
- **Respect for robots.txt**: Follows website guidelines and restrictions
- **Educational Use**: Intended for personal exam preparation only
- **No Commercial Use**: Not intended for commercial distribution or profit

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   ```bash
   # Re-authenticate with Google Cloud
   gcloud auth application-default login
   ```

2. **Missing Dependencies**:
   ```bash
   # Reinstall with all dependencies
   uv sync --all-extras
   ```

3. **Extraction Failures**:
   - Check internet connection
   - Verify exam URL is accessible
   - Enable verbose mode for detailed error messages

4. **No Exams Found**:
   - Run extraction command first
   - Check data directory permissions
   - Validate extracted data

### Debug Mode

Enable debug mode for detailed logging:

```bash
uv run cert-examtopics-quiz extract "URL" --debug
uv run cert-examtopics-quiz quiz --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite and linting
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This application is for educational purposes only. Users are responsible for ensuring their use complies with ExamTopics' terms of service and applicable laws. The authors are not responsible for any misuse of this software.
