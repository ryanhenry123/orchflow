from orchflow.evals.checks import (
    fail_on_filter,
    min_length,
    require_sections,
    stop_not_truncated,
    word_count,
)

SIMPLE_EVALS = [
    fail_on_filter(),
    stop_not_truncated(name="not_truncated"),
    require_sections("## Summary", "## Key Points", name="structure"),
    word_count(min=30, max=200, name="brevity"),
    min_length(
        40,
        msg="Summary must be at least 40 characters total",
        name="min_length",
    ),
]
