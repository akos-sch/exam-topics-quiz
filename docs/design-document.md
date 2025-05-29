# Certificate ExamTopics Quiz - Design Document

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Extractor Module Design](#extractor-module-design)
4. [Questionnaire Module Design](#questionnaire-module-design)
5. [Data Models](#data-models)
6. [Implementation Details](#implementation-details)
7. [Configuration](#configuration)
8. [Error Handling](#error-handling)
9. [Testing Strategy](#testing-strategy)
10. [Future Enhancements](#future-enhancements)

## Overview

The Certificate ExamTopics Quiz application is designed to extract exam questions from the ExamTopics website and provide an interactive quiz interface for exam preparation. The application consists of two main modules:

1. **Extractor Module**: Responsible for web scraping, data extraction, and local storage
2. **Questionnaire Module**: Provides various interfaces (CLI, GUI) for taking quizzes

### Goals
- Extract comprehensive exam data from ExamTopics website
- Store questions, answers, and community discussions locally
- Provide flexible quiz interfaces for different user preferences
- Maintain data integrity and handle edge cases gracefully

### Non-Goals
- Real-time synchronization with ExamTopics
- User authentication or progress tracking across sessions
- Commercial distribution or violation of ExamTopics terms of service

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ExamTopics Website                       │
│  https://www.examtopics.com/exams/google/professional-...   │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP Requests
                      │ (with rate limiting)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Extractor Module                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Scraper   │  │   Parser    │  │   Storage Manager   │  │
│  │             │  │             │  │                     │  │
│  │ - Rate      │  │ - HTML      │  │ - JSON Files        │  │
│  │   Limiting  │  │   Parsing   │  │ - Data Validation   │  │
│  │ - Session   │  │ - Data      │  │ - File Organization │  │
│  │   Management│  │   Extraction│  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Structured Data
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Local Storage                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │   Questions     │  │   Discussions   │  │   Metadata  │  │
│  │   (JSON)        │  │   (JSON)        │  │   (JSON)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ Data Access
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                Questionnaire Module                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ CLI Interface│  │ Data Loader │  │  Quiz Engine        │  │
│  │             │  │             │  │                     │  │
│  │ - Interactive│  │ - Question  │  │ - Scoring           │  │
│  │   Prompts   │  │   Selection │  │ - Progress Tracking │  │
│  │ - Progress  │  │ - Filtering │  │ - Answer Validation │  │
│  │   Display   │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Extractor Module Design

### Core Components

#### 1. Web Scraper (`extractor/scraper.py`)

**Responsibilities:**
- Manage HTTP sessions with proper headers and rate limiting
- Navigate through paginated question lists
- Handle authentication if required
- Implement retry logic for failed requests
- Respect robots.txt and implement ethical scraping practices

**Key Features:**
```python
class ExamTopicsScraper:
    def __init__(self, base_url: str, rate_limit: float = 1.0):
        self.session = requests.Session()
        self.rate_limit = rate_limit
        self.last_request_time = 0

    def get_exam_pages(self, exam_url: str) -> List[str]:
        """Get all page URLs for an exam"""

    def get_page_content(self, url: str) -> BeautifulSoup:
        """Fetch and parse a single page with rate limiting"""

    def get_question_details(self, question_id: str) -> Dict:
        """Fetch detailed question data including discussions"""
```

#### 2. HTML Parser (`extractor/parser.py`)

**Responsibilities:**
- Parse question cards from HTML content using LangChain structured output
- Extract question text, choices, and metadata into Pydantic models
- Parse discussion threads and comments with structured extraction
- Handle malformed HTML gracefully with validation
- Extract voting data and community statistics

**LangChain Structured Output Approach:**

The parser leverages LangChain's `with_structured_output` method to convert raw HTML content into structured Pydantic models. This approach provides several advantages:

- **Type Safety**: Automatic validation of extracted data
- **Error Handling**: Built-in parsing error detection and recovery
- **Consistency**: Standardized extraction across different question formats
- **Maintainability**: Clear schema definitions for all data structures

**Parser Implementation:**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from bs4 import BeautifulSoup

class Choice(BaseModel):
    """Represents a multiple choice option"""
    letter: str = Field(description="Choice letter (A, B, C, D)")
    text: str = Field(description="The full text of the choice")
    is_most_voted: bool = Field(default=False, description="Whether this is the most voted answer")

class VotingData(BaseModel):
    """Community voting statistics"""
    total_votes: int = Field(description="Total number of votes")
    vote_distribution: dict[str, int] = Field(description="Vote count per choice letter")
    most_voted_answer: str = Field(description="The choice letter with most votes")
    confidence_score: float = Field(description="Confidence based on vote distribution")

class Question(BaseModel):
    """Complete question data structure"""
    id: str = Field(description="Unique question identifier")
    number: int = Field(description="Question number in the exam")
    topic: str = Field(description="Topic or section name")
    text: str = Field(description="The question text content")
    choices: List[Choice] = Field(description="List of multiple choice options")
    correct_answer: str = Field(description="The correct answer choice letter")
    explanation: Optional[str] = Field(default=None, description="Explanation of the answer")
    voting_data: VotingData = Field(description="Community voting statistics")

class Comment(BaseModel):
    """Discussion comment structure"""
    id: str = Field(description="Comment identifier")
    author: str = Field(description="Comment author username")
    content: str = Field(description="Comment text content")
    upvotes: int = Field(description="Number of upvotes")
    is_highly_voted: bool = Field(default=False, description="Whether comment is highly voted")
    timestamp: str = Field(description="Comment timestamp")

class Discussion(BaseModel):
    """Discussion thread for a question"""
    question_id: str = Field(description="Associated question ID")
    total_comments: int = Field(description="Total number of comments")
    comments: List[Comment] = Field(description="List of discussion comments")

class QuestionParser:
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        # Uses Google Application Default Credentials
        self.llm = ChatVertexAI(
            model_name="gemini-2.0-flash-001",
            temperature=0,
            project=project_id,
            location=location
        )
        self.question_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting structured data from HTML content.
            Extract question information from ExamTopics question cards with high accuracy.
            Pay special attention to:
            - Question numbering and ID extraction
            - Multiple choice options (A, B, C, D)
            - Correct answer identification
            - Community voting data from JSON scripts
            - Any explanations or additional context"""),
            ("human", "Extract the question data from this HTML:\n\n{html_content}")
        ])

        self.discussion_prompt = ChatPromptTemplate.from_messages([
            ("system", """Extract discussion thread data from ExamTopics modal content.
            Focus on:
            - Individual comment extraction
            - Author information
            - Upvote counts and highly voted status
            - Comment timestamps and content
            - Nested replies if present"""),
            ("human", "Extract the discussion data from this HTML:\n\n{html_content}")
        ])

        self.structured_question_llm = self.llm.with_structured_output(Question)
        self.structured_discussion_llm = self.llm.with_structured_output(Discussion)

    def parse_question_card(self, soup: BeautifulSoup) -> Question:
        """Extract question data using LangChain structured output"""
        html_content = str(soup)
        prompt = self.question_prompt.invoke({"html_content": html_content})
        return self.structured_question_llm.invoke(prompt)

    def parse_discussion(self, modal_soup: BeautifulSoup, question_id: str) -> Discussion:
        """Extract discussion data using LangChain structured output"""
        html_content = str(modal_soup)
        prompt = self.discussion_prompt.invoke({"html_content": html_content})
        discussion = self.structured_discussion_llm.invoke(prompt)
        discussion.question_id = question_id  # Ensure correct association
        return discussion

    def parse_voting_data_from_json(self, script_content: str) -> VotingData:
        """Parse voting data from embedded JSON scripts"""
        voting_prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract voting statistics from this JSON data"),
            ("human", "Parse voting data: {json_content}")
        ])
        structured_voting_llm = self.llm.with_structured_output(VotingData)
        prompt = voting_prompt.invoke({"json_content": script_content})
        return structured_voting_llm.invoke(prompt)
```

**Benefits of LangChain Structured Output:**

1. **Robust Parsing**: LLM can handle variations in HTML structure and content
2. **Data Validation**: Pydantic models ensure data integrity and type safety
3. **Error Recovery**: Graceful handling of malformed or incomplete HTML
4. **Flexibility**: Easy to adapt to changes in ExamTopics HTML structure
5. **Rich Context Understanding**: LLM can interpret complex nested structures
6. **Automatic Cleaning**: LLM naturally handles HTML artifacts and formatting issues

#### 3. Storage Manager (`extractor/storage.py`)

**Responsibilities:**
- Organize extracted data into structured files
- Implement data validation and integrity checks
- Handle incremental updates and deduplication
- Provide data versioning and backup capabilities
- Optimize storage format for quick access

**Storage Structure:**
```
data/
├── exams/
│   └── google-professional-ml-engineer/
│       ├── metadata.json
│       ├── questions/
│       │   ├── question_001.json
│       │   ├── question_002.json
│       │   └── ...
│       └── discussions/
│           ├── discussion_001.json
│           ├── discussion_002.json
│           └── ...
└── cache/
    ├── pages/
    └── sessions/
```

### Extraction Workflow

1. **Initialization**
   - Load configuration (target exams, rate limits, storage paths)
   - Initialize HTTP session with appropriate headers
   - Create storage directory structure

2. **Exam Discovery**
   - Navigate to exam main page
   - Extract total question count and page structure
   - Generate list of all question page URLs

3. **Question Extraction**
   - Iterate through all question pages with rate limiting
   - Parse each question card for basic data
   - Extract question ID for detailed fetching

4. **Detailed Data Extraction**
   - For each question, fetch additional details
   - Extract discussion data if available
   - Parse voting statistics and community data

5. **Data Storage**
   - Validate extracted data against schema
   - Store questions and discussions in structured format
   - Update metadata and create indexes

6. **Verification**
   - Verify data integrity and completeness
   - Generate extraction report
   - Log any errors or missing data

## Questionnaire Module Design

### Core Components

#### 1. Data Loader (`questionnaire/loader.py`)

**Responsibilities:**
- Load questions from local storage
- Implement filtering and selection criteria
- Provide question randomization
- Handle data caching for performance

#### 2. Quiz Engine (`questionnaire/engine.py`)

**Responsibilities:**
- Manage quiz session state
- Handle answer validation and scoring
- Track progress and timing
- Generate quiz results and statistics

#### 3. Interface Implementations

**CLI Interface (`questionnaire/cli.py`):**
- Interactive command-line quiz experience
- Progress indicators and real-time feedback
- Configurable display options

**Future Interfaces:**
- Web interface using Flask/FastAPI
- Desktop GUI using tkinter or PyQt
- API interface for integration with other tools

## Data Models

The application uses Pydantic models for all data structures, providing automatic validation, serialization, and integration with LangChain's structured output capabilities.

### Core Question Models
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class Choice(BaseModel):
    """Represents a multiple choice option"""
    letter: str = Field(description="Choice letter (A, B, C, D)")
    text: str = Field(description="The full text of the choice")
    is_most_voted: bool = Field(default=False, description="Whether this is the most voted answer")
    is_correct: bool = Field(default=False, description="Whether this is the correct answer")

class VotingData(BaseModel):
    """Community voting statistics"""
    total_votes: int = Field(description="Total number of votes")
    vote_distribution: Dict[str, int] = Field(description="Vote count per choice letter")
    most_voted_answer: str = Field(description="The choice letter with most votes")
    confidence_score: float = Field(description="Confidence based on vote distribution")

class QuestionMetadata(BaseModel):
    """Additional question metadata"""
    extraction_timestamp: datetime = Field(description="When the question was extracted")
    source_url: str = Field(description="Original URL of the question")
    page_number: int = Field(description="Page number in the exam")
    difficulty_level: Optional[str] = Field(default=None, description="Estimated difficulty")

class Question(BaseModel):
    """Complete question data structure"""
    id: str = Field(description="Unique question identifier")
    number: int = Field(description="Question number in the exam")
    topic: str = Field(description="Topic or section name")
    text: str = Field(description="The question text content")
    choices: List[Choice] = Field(description="List of multiple choice options")
    correct_answer: str = Field(description="The correct answer choice letter")
    explanation: Optional[str] = Field(default=None, description="Explanation of the answer")
    voting_data: VotingData = Field(description="Community voting statistics")
    metadata: QuestionMetadata = Field(description="Additional metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Discussion Models
```python
class Comment(BaseModel):
    """Discussion comment structure"""
    id: str = Field(description="Comment identifier")
    author: str = Field(description="Comment author username")
    content: str = Field(description="Comment text content")
    upvotes: int = Field(description="Number of upvotes")
    is_highly_voted: bool = Field(default=False, description="Whether comment is highly voted")
    timestamp: str = Field(description="Comment timestamp")
    replies: List['Comment'] = Field(default_factory=list, description="Nested replies")

    class Config:
        # Enable forward references for self-referencing model
        arbitrary_types_allowed = True

class Discussion(BaseModel):
    """Discussion thread for a question"""
    question_id: str = Field(description="Associated question ID")
    total_comments: int = Field(description="Total number of comments")
    comments: List[Comment] = Field(description="List of discussion comments")
    extraction_timestamp: datetime = Field(description="When discussion was extracted")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Update forward references
Comment.model_rebuild()
```

### Quiz Session Models
```python
class QuizSettings(BaseModel):
    """Quiz configuration settings"""
    question_count: int = Field(description="Number of questions in quiz")
    time_limit: Optional[int] = Field(default=None, description="Time limit in seconds")
    randomize_questions: bool = Field(default=True, description="Whether to randomize question order")
    randomize_choices: bool = Field(default=False, description="Whether to randomize choice order")
    show_explanations: bool = Field(default=True, description="Whether to show explanations")

class UserAnswer(BaseModel):
    """User's answer to a question"""
    question_id: str = Field(description="Question identifier")
    selected_choice: str = Field(description="Selected choice letter")
    is_correct: bool = Field(description="Whether the answer is correct")
    time_taken: float = Field(description="Time taken to answer in seconds")
    timestamp: datetime = Field(description="When the answer was submitted")

class QuizResult(BaseModel):
    """Quiz completion results"""
    total_questions: int = Field(description="Total number of questions")
    correct_answers: int = Field(description="Number of correct answers")
    score_percentage: float = Field(description="Score as percentage")
    total_time: float = Field(description="Total time taken in seconds")
    average_time_per_question: float = Field(description="Average time per question")

class QuizSession(BaseModel):
    """Complete quiz session data"""
    session_id: str = Field(description="Unique session identifier")
    exam_name: str = Field(description="Name of the exam")
    settings: QuizSettings = Field(description="Quiz configuration")
    questions: List[Question] = Field(description="Questions in the quiz")
    user_answers: List[UserAnswer] = Field(default_factory=list, description="User's answers")
    start_time: datetime = Field(description="Quiz start time")
    end_time: Optional[datetime] = Field(default=None, description="Quiz end time")
    result: Optional[QuizResult] = Field(default=None, description="Quiz results")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

### Exam Metadata Models
```python
class ExamInfo(BaseModel):
    """Information about an exam"""
    name: str = Field(description="Exam name")
    vendor: str = Field(description="Exam vendor (e.g., Google, AWS)")
    code: str = Field(description="Exam code")
    total_questions: int = Field(description="Total number of questions available")
    url: str = Field(description="Source URL")
    last_updated: datetime = Field(description="Last extraction timestamp")

class ExtractionReport(BaseModel):
    """Report of extraction process"""
    exam_info: ExamInfo = Field(description="Exam information")
    questions_extracted: int = Field(description="Number of questions extracted")
    discussions_extracted: int = Field(description="Number of discussions extracted")
    extraction_errors: List[str] = Field(default_factory=list, description="Extraction errors")
    start_time: datetime = Field(description="Extraction start time")
    end_time: datetime = Field(description="Extraction end time")
    success: bool = Field(description="Whether extraction was successful")
```

### Benefits of Pydantic Models

1. **Automatic Validation**: Type checking and data validation at runtime
2. **JSON Serialization**: Built-in JSON encoding/decoding capabilities
3. **Documentation**: Self-documenting with field descriptions
4. **IDE Support**: Full type hints and autocompletion
5. **LangChain Integration**: Native compatibility with structured output
6. **Data Migration**: Easy schema evolution and migration support

## Implementation Details

### LangChain Integration Strategy

**Structured Output Pipeline:**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain_core.runnables import RunnablePassthrough

class ExtractionPipeline:
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        # Uses Google Application Default Credentials automatically
        self.llm = ChatVertexAI(
            model_name="gemini-2.0-flash-001",
            temperature=0,
            project=project_id,  # Optional, uses default project if None
            location=location
        )

    def create_extraction_chain(self, schema: BaseModel, system_prompt: str):
        """Create a reusable extraction chain for any schema"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Extract data from this content:\n\n{content}")
        ])

        structured_llm = self.llm.with_structured_output(schema)
        return prompt | structured_llm

    def extract_with_fallback(self, chain, content: str, max_retries: int = 3):
        """Extract with retry logic and error handling"""
        for attempt in range(max_retries):
            try:
                return chain.invoke({"content": content})
            except Exception as e:
                if attempt == max_retries - 1:
                    # Log error and return None or default structure
                    logger.error(f"Extraction failed after {max_retries} attempts: {e}")
                    return None
                time.sleep(2 ** attempt)  # Exponential backoff
```

**Few-Shot Prompting for Better Accuracy:**
```python
def create_question_extraction_prompt():
    """Create prompt with few-shot examples for question extraction"""
    return ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting structured data from ExamTopics HTML.

        Here are some examples of correct extractions:

        Example 1:
        HTML: <div class="card-header">Question #15</div>...
        Output: {{"number": 15, "id": "question_15", ...}}

        Example 2:
        HTML: <span class="correct-answer">B</span>...
        Output: {{"correct_answer": "B", ...}}

        Always extract:
        - Question number and generate consistent ID
        - All choice options with letters A, B, C, D
        - Correct answer from the reveal section
        - Community voting data if present
        """),
        ("human", "Extract the question data from this HTML:\n\n{html_content}")
    ])
```

### Rate Limiting Strategy
- Implement exponential backoff for failed requests
- Respect server response times and adjust delays
- Use random jitter to avoid thundering herd effects
- Monitor for rate limiting responses (429 status codes)
- **LLM Rate Limiting**: Manage Google Vertex AI rate limits for extraction calls

### Error Handling
- Graceful degradation for missing data
- Retry logic with maximum attempt limits
- Comprehensive logging for debugging
- Data validation at multiple levels
- **LLM Error Handling**: Fallback to traditional parsing if LLM extraction fails
- **Schema Validation**: Pydantic validation with detailed error messages

### Performance Optimization
- Implement concurrent processing where appropriate
- Use connection pooling for HTTP requests
- Cache parsed data to avoid re-processing
- Optimize file I/O operations
- **LLM Optimization**:
  - Batch multiple extractions in single requests when possible
  - Cache LLM responses for identical HTML content
  - Use streaming for large content processing
  - Implement smart content chunking for large pages

### Data Integrity
- Implement checksums for stored data
- Validate data schema on load/save
- Handle partial extraction scenarios
- Provide data repair and recovery tools
- **Pydantic Validation**: Automatic type checking and data validation
- **Cross-Validation**: Compare LLM extraction with traditional parsing methods

## Configuration

### Extractor Configuration (`config/extractor.yaml`)
```yaml
scraping:
  rate_limit: 1.0  # seconds between requests
  max_retries: 3
  timeout: 30
  user_agent: "ExamTopics Quiz Extractor 1.0"

llm:
  provider: "google_vertexai"
  model: "gemini-2.0-flash-001"
  project_id: "${GOOGLE_CLOUD_PROJECT}"  # Optional, uses default project if not set
  location: "us-central1"  # GCP region
  temperature: 0
  max_tokens: 4000
  rate_limit: 60  # requests per minute
  max_retries: 3
  fallback_to_traditional_parsing: true
  # Uses Google Application Default Credentials automatically

extraction:
  use_structured_output: true
  batch_size: 5  # questions to process in parallel
  cache_llm_responses: true
  validate_with_traditional_parser: true
  few_shot_examples: true

storage:
  base_path: "./data"
  backup_enabled: true
  compression: true

exams:
  - name: "google-professional-ml-engineer"
    url: "https://www.examtopics.com/exams/google/professional-machine-learning-engineer/"
    total_questions: 321
    extract_discussions: true
    use_llm_extraction: true
```

### Questionnaire Configuration (`config/questionnaire.yaml`)
```yaml
quiz:
  default_question_count: 10
  time_limit: 1800  # 30 minutes
  randomize_questions: true
  randomize_choices: false
  show_explanations: true

display:
  show_progress: true
  show_timer: true
  clear_screen: true
  color_output: true
```

## Error Handling

### Extraction Errors
- **Network Issues**: Implement retry with exponential backoff
- **Parsing Errors**: Log and continue with next question
- **Storage Errors**: Validate data and provide recovery options
- **Rate Limiting**: Respect server limits and adjust timing

### Quiz Errors
- **Missing Data**: Graceful fallback to available questions
- **Invalid Input**: Clear error messages and input validation
- **Session Corruption**: Auto-save and recovery mechanisms

## Testing Strategy

### Unit Tests
- Test individual parser functions with sample HTML
- Validate data models and serialization
- Test quiz logic and scoring algorithms

### Integration Tests
- Test complete extraction workflow with mock data
- Validate storage and retrieval operations
- Test quiz session management

### End-to-End Tests
- Test complete user workflows
- Validate data integrity across modules
- Performance testing with large datasets

### Test Data
- Create sample HTML files for parser testing
- Generate synthetic question data for quiz testing
- Mock HTTP responses for scraper testing

## Future Enhancements

### Phase 2 Features
- Support for multiple exam providers
- Advanced filtering and search capabilities
- Progress tracking across sessions
- Export functionality (PDF, CSV)

### Phase 3 Features
- Web-based interface
- User accounts and progress synchronization
- Advanced analytics and performance insights
- Mobile application support

### Technical Improvements
- Database backend for better performance
- Distributed extraction for large datasets
- Real-time updates and synchronization
- Advanced caching strategies

## Security Considerations

### Data Privacy
- No collection of personal user data
- Local storage only for extracted content
- Respect for ExamTopics terms of service

### Ethical Scraping
- Implement reasonable rate limits
- Respect robots.txt directives
- Monitor server load and adjust accordingly
- Provide clear attribution and usage guidelines

## Deployment and Distribution

### Package Structure
```
cert-examtopics-quiz/
├── src/cert_examtopics_quiz/
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── scraper.py
│   │   ├── parser.py          # LangChain + Gemini integration
│   │   └── storage.py
│   ├── questionnaire/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   ├── engine.py
│   │   └── cli.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── question.py        # Pydantic models
│   │   ├── session.py
│   │   └── extraction.py      # Extraction-specific models
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── gcp.py            # Google Cloud configuration
│   └── utils/
│       ├── __init__.py
│       ├── auth.py           # GCP authentication helpers
│       └── prompts.py        # LangChain prompt templates
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│       └── sample_html/      # Sample ExamTopics HTML for testing
├── docs/
├── config/
│   ├── extractor.yaml
│   └── questionnaire.yaml
└── data/
    ├── exams/
    └── cache/
```

### Installation Methods
- PyPI package distribution
- Docker container for isolated execution
- Standalone executable for non-Python users
- Development installation from source

### Google Cloud Setup

**Prerequisites:**
1. Google Cloud Project with Vertex AI API enabled
2. Application Default Credentials configured
3. Required Python packages installed

**Setup Steps:**
```bash
# Install required packages
pip install -U langchain-google-vertexai

# Authenticate with Google Cloud (if not already done)
gcloud auth application-default login

# Set default project (optional)
gcloud config set project YOUR_PROJECT_ID

# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com
```

**Environment Variables:**
```bash
# Optional - will use default project if not set
export GOOGLE_CLOUD_PROJECT=your-project-id

# Optional - will use default region if not set
export GOOGLE_CLOUD_REGION=us-central1
```

**Authentication Methods:**
1. **Application Default Credentials** (Recommended for development)
   - `gcloud auth application-default login`
   - Automatically used by the application

2. **Service Account Key** (For production)
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Point to service account JSON key file

3. **Compute Engine/Cloud Run** (For deployed applications)
   - Uses attached service account automatically
   - No additional configuration needed

**Required IAM Permissions:**
- `aiplatform.endpoints.predict`
- `aiplatform.models.predict`
- `ml.models.predict` (for legacy models)

This design document provides a comprehensive foundation for implementing the ExamTopics quiz application with a focus on robust data extraction using Google's Gemini models and flexible quiz interfaces.
