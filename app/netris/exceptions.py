class NetrisError(Exception):
    """Base class for anything that goes wrong talking to the Netris controller."""


class NetrisAuthError(NetrisError):
    """Login failed, or a call kept failing auth even after a re-login attempt."""


class NetrisAPIError(NetrisError):
    """Netris responded but with an error (non-2xx, or isSuccess: false)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NetrisCapacityError(NetrisError):
    """Not enough unassigned servers at the configured site to satisfy a request."""

    def __init__(self, requested: int, available: int):
        super().__init__(
            f"Requested {requested} GPU server(s) but only {available} are available at the configured site."
        )
        self.requested = requested
        self.available = available
