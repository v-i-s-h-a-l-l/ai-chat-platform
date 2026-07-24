from app.services.response_formatter import format_assistant_response


def test_converts_table_with_lists_in_cells():
    raw = """Here is your plan:

| Stage | Preparation |
|-------|-------------|
| Technical | 1. Learn Spark
2. Learn Python
3. Learn ML |
| Resources | - Spark docs
- Airflow guide |

Good luck!"""

    result = format_assistant_response(raw)

    assert "| Stage |" not in result
    assert "## Technical" in result
    assert "1. Learn Spark" in result
    assert "## Resources" in result
    assert "- Spark docs" in result
    assert "Good luck!" in result


def test_converts_three_column_table_with_long_cells():
    raw = """| Interview Stage | JD Expectations | Preparation |
|---|---|---|
| Aptitude | General problem solving and logical reasoning skills | Solve 30-40 aptitude questions daily and complete one mock test in under 30 minutes |
| Communication | Clear communication and concise writing ability | Record a 2-minute introduction and practice business summaries every day |"""

    result = format_assistant_response(raw)

    assert "| Interview Stage |" not in result
    assert "### Aptitude" in result
    assert "**JD Expectations**" in result
    assert "**Preparation**" in result


def test_keeps_short_comparison_table():
    raw = """| Plan | Price | Storage |
|---|---|---|
| Free | $0 | 5 GB |
| Pro | $10 | 100 GB |"""

    result = format_assistant_response(raw)

    assert "| Plan | Price | Storage |" in result
    assert "| Free | $0 | 5 GB |" in result


def test_converts_oversized_cell_by_char_count():
    long_text = "x" * 151
    raw = f"""| Topic | Notes |
|---|---|
| Alpha | {long_text} |"""

    result = format_assistant_response(raw)

    assert "| Topic |" not in result
    assert "## Alpha" in result
    assert long_text in result


def test_preserves_fenced_code_blocks():
    raw = """```python
| not | a table |
```

| Stage | Prep |
|---|---|
| Tech | - item one
- item two |"""

    result = format_assistant_response(raw)

    assert "```python\n| not | a table |\n```" in result
    assert "## Tech" in result
    assert "- item one" in result


def test_normalizes_spacing_around_lists():
    raw = """Intro line
- one
- two
Next paragraph"""

    result = format_assistant_response(raw)

    assert "- one\n- two" in result
    assert "Intro line\n\n- one" in result
