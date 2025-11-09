"""
TAMS Client Exceptions

Custom exception hierarchy for TAMS client operations.
"""


class TAMSClientError(Exception):
    """Base exception for all TAMS client errors."""
    pass


class TAMSAuthenticationError(TAMSClientError):
    """Exception raised for authentication errors."""
    pass


class TAMSAPIError(TAMSClientError):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
    
    def __str__(self):
        msg = super().__str__()
        if self.status_code:
            msg = f"[{self.status_code}] {msg}"
        if self.response_body:
            msg = f"{msg}\nResponse: {self.response_body}"
        return msg


class TAMSConnectionError(TAMSClientError):
    """Exception raised for connection errors."""
    pass

