"""
Tests for TAMS client exceptions.
"""

import pytest
from vasttamsclient.exceptions import (
    TAMSClientError,
    TAMSAuthenticationError,
    TAMSAPIError,
    TAMSConnectionError
)


class TestTAMSClientError:
    """Tests for base TAMSClientError."""
    
    def test_base_exception(self):
        """Test base exception can be raised."""
        with pytest.raises(TAMSClientError):
            raise TAMSClientError("Test error")
    
    def test_base_exception_message(self):
        """Test base exception message."""
        error = TAMSClientError("Test error message")
        assert str(error) == "Test error message"


class TestTAMSAuthenticationError:
    """Tests for TAMSAuthenticationError."""
    
    def test_authentication_error(self):
        """Test authentication error can be raised."""
        with pytest.raises(TAMSAuthenticationError):
            raise TAMSAuthenticationError("Authentication failed")
    
    def test_authentication_error_inheritance(self):
        """Test authentication error inherits from base."""
        error = TAMSAuthenticationError("Auth failed")
        assert isinstance(error, TAMSClientError)


class TestTAMSAPIError:
    """Tests for TAMSAPIError."""
    
    def test_api_error_basic(self):
        """Test API error with message only."""
        error = TAMSAPIError("API error")
        assert str(error) == "API error"
        assert error.status_code is None
        assert error.response_body is None
    
    def test_api_error_with_status_code(self):
        """Test API error with status code."""
        error = TAMSAPIError("Not found", status_code=404)
        assert "[404]" in str(error)
        assert "Not found" in str(error)
        assert error.status_code == 404
    
    def test_api_error_with_response_body(self):
        """Test API error with response body."""
        error = TAMSAPIError("Error", status_code=400, response_body='{"error": "bad request"}')
        assert "[400]" in str(error)
        assert "Error" in str(error)
        assert "Response:" in str(error)
        assert '{"error": "bad request"}' in str(error)
    
    def test_api_error_inheritance(self):
        """Test API error inherits from base."""
        error = TAMSAPIError("API error")
        assert isinstance(error, TAMSClientError)


class TestTAMSConnectionError:
    """Tests for TAMSConnectionError."""
    
    def test_connection_error(self):
        """Test connection error can be raised."""
        with pytest.raises(TAMSConnectionError):
            raise TAMSConnectionError("Connection failed")
    
    def test_connection_error_inheritance(self):
        """Test connection error inherits from base."""
        error = TAMSConnectionError("Connection failed")
        assert isinstance(error, TAMSClientError)

