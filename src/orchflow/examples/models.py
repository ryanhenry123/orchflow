from os import getenv

DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-6"

MODEL = getenv("ORCHFLOW_MODEL", DEFAULT_MODEL)
