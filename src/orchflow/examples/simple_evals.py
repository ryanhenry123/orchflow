from orchflow.evals.checks import min_length
from orchflow.panels import markdown_sections, no_preamble

SIMPLE_EVALS = [
    *markdown_sections(
        "## Summary",
        "## Key Points",
        min_words=30,
        max_words=200,
    ),
    no_preamble(),
    min_length(
        40, msg="Summary must be at least 40 characters total", name="min_length"
    ),
]
