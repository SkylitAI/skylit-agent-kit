"""Messages controlled by the use-case implementation, safe for CLI display."""


class UseCaseError(ValueError):
    """An actionable validation error that never embeds raw source content."""
