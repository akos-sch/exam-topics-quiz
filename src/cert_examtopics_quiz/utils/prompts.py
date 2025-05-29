"""LangChain prompt templates for structured data extraction."""

from langchain_core.prompts import ChatPromptTemplate


def get_question_extraction_prompt() -> ChatPromptTemplate:
    """Create prompt template for question extraction with few-shot examples."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert at extracting structured data from ExamTopics HTML content.
        Extract question information from ExamTopics question cards with high accuracy.

        Pay special attention to:
        - Question numbering and ID extraction from headers like "Question #15"
        - Multiple choice options (A, B, C, D) with their full text
        - Correct answer identification from reveal sections
        - Community voting data from embedded JSON scripts or vote counts
        - Any explanations or additional context
        - Topic/section information

        Here are some examples of correct extractions:

        Example 1:
        HTML: <div class="card-header">Question #15 Topic 1</div>
              <div class="question-body">What is the best practice for...</div>
              <div class="choices">
                <div class="choice">A. Option A text</div>
                <div class="choice">B. Option B text</div>
              </div>
              <span class="correct-answer">B</span>
        Output: {{
          "number": 15,
          "id": "question_15",
          "topic": "Topic 1",
          "text": "What is the best practice for...",
          "choices": [
            {{"letter": "A", "text": "Option A text", "is_correct": false}},
            {{"letter": "B", "text": "Option B text", "is_correct": true}}
          ],
          "correct_answer": "B"
        }}

        Always extract:
        - Question number and generate consistent ID format "question_{{number}}"
        - All choice options with letters A, B, C, D and their full text
        - Correct answer from the reveal section or marked answers
        - Community voting data if present (vote counts, percentages)
        - Calculate confidence score based on vote distribution
        - Extract any explanations provided
        """,
            ),
            ("human", "Extract the question data from this HTML:\n\n{html_content}"),
        ]
    )


def get_discussion_extraction_prompt() -> ChatPromptTemplate:
    """Create prompt template for discussion extraction."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Extract discussion thread data from ExamTopics modal content.

        Focus on extracting:
        - Individual comment extraction with unique IDs
        - Author information (usernames)
        - Comment content (full text)
        - Upvote counts and highly voted status (usually comments with >10 upvotes)
        - Comment timestamps if available
        - Nested replies if present (replies to other comments)
        - Total comment count

        Structure the data hierarchically:
        - Main comments at the top level
        - Replies nested under their parent comments
        - Preserve the discussion flow and context

        Mark comments as "highly_voted" if they have significant upvotes (>10) or are marked as helpful.
        Generate consistent comment IDs in format "comment_{{index}}" or use existing IDs if available.
        """,
            ),
            ("human", "Extract the discussion data from this HTML:\n\n{html_content}"),
        ]
    )


def get_voting_data_extraction_prompt() -> ChatPromptTemplate:
    """Create prompt template for voting data extraction from JSON scripts."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Extract voting statistics from embedded JSON data or vote count elements.

        Look for:
        - Total vote counts
        - Vote distribution per choice (A, B, C, D)
        - Percentages for each choice
        - Most voted answer identification
        - Calculate confidence score based on vote distribution

        Confidence score calculation:
        - High confidence (0.8-1.0): Clear majority vote (>60% for one answer)
        - Medium confidence (0.5-0.8): Moderate majority (40-60% for top answer)
        - Low confidence (0.0-0.5): Split votes or unclear majority (<40% for top answer)
        """,
            ),
            ("human", "Parse voting data from this content: {json_content}"),
        ]
    )


def get_metadata_extraction_prompt() -> ChatPromptTemplate:
    """Create prompt template for extracting question metadata."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Extract metadata information from the question page.

        Extract:
        - Page number or position in the exam
        - Difficulty level if indicated
        - Topic or section classification
        - Any tags or categories
        - Source URL information
        - Last updated timestamps if available

        Estimate difficulty level based on:
        - Question complexity and length
        - Number of choices and their complexity
        - Community discussion volume and confusion
        - Vote distribution (unclear votes might indicate higher difficulty)
        """,
            ),
            ("human", "Extract metadata from this content: {content}"),
        ]
    )
