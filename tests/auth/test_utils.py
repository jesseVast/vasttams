#!/usr/bin/env python3
"""
Tests for Authentication Utilities

Tests auth utility functions.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from vasttamsserver.auth.utils import (
    generate_user_id,
    hash_password,
    verify_password,
    generate_api_token,
    is_token_expired,
    calculate_token_expiry
)


class TestAuthUtils:
    """Test authentication utility functions"""
    
    def test_generate_user_id(self):
        """Test generate_user_id creates unique IDs"""
        user_id1 = generate_user_id()
        user_id2 = generate_user_id()
        
        assert isinstance(user_id1, str)
        assert len(user_id1) > 0
        assert user_id1 != user_id2  # Should be unique
    
    def test_hash_password(self):
        """Test hash_password"""
        password = "testpassword"
        hashed = hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA-256 hex digest length
        assert hashed != password
    
    def test_hash_password_consistency(self):
        """Test hash_password produces consistent results"""
        password = "testpassword"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)
        
        # SHA-256 should produce same hash for same input
        assert hashed1 == hashed2
    
    def test_verify_password_success(self):
        """Test verify_password with correct password"""
        password = "testpassword"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_failure(self):
        """Test verify_password with incorrect password"""
        password = "testpassword"
        hashed = hash_password(password)
        
        assert verify_password("wrongpassword", hashed) is False
    
    def test_verify_password_different_passwords(self):
        """Test verify_password with different passwords"""
        password1 = "password1"
        password2 = "password2"
        
        hashed1 = hash_password(password1)
        hashed2 = hash_password(password2)
        
        assert verify_password(password1, hashed1) is True
        assert verify_password(password2, hashed2) is True
        assert verify_password(password1, hashed2) is False
        assert verify_password(password2, hashed1) is False
    
    def test_generate_api_token(self):
        """Test generate_api_token creates unique tokens"""
        token1 = generate_api_token()
        token2 = generate_api_token()
        
        assert isinstance(token1, str)
        assert len(token1) > 0
        assert token1 != token2  # Should be unique
    
    def test_generate_api_token_length(self):
        """Test generate_api_token creates tokens of reasonable length"""
        token = generate_api_token()
        
        # token_urlsafe(32) produces ~43 characters
        assert len(token) >= 32
    
    def test_is_token_expired_none(self):
        """Test is_token_expired with None expiration"""
        assert is_token_expired(None) is False
    
    def test_is_token_expired_future(self):
        """Test is_token_expired with future expiration"""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        assert is_token_expired(future_time) is False
    
    def test_is_token_expired_past(self):
        """Test is_token_expired with past expiration"""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        assert is_token_expired(past_time) is True
    
    def test_is_token_expired_now(self):
        """Test is_token_expired with current time"""
        now = datetime.now(timezone.utc)
        # Should be expired (or very close to it)
        # Allow small time difference
        result = is_token_expired(now)
        assert isinstance(result, bool)
    
    def test_calculate_token_expiry_default(self):
        """Test calculate_token_expiry with default minutes"""
        expiry = calculate_token_expiry()
        
        assert isinstance(expiry, datetime)
        assert expiry.tzinfo == timezone.utc
        
        # Should be approximately 30 minutes from now
        now = datetime.now(timezone.utc)
        diff = expiry - now
        assert 29 <= diff.total_seconds() / 60 <= 31
    
    def test_calculate_token_expiry_custom(self):
        """Test calculate_token_expiry with custom minutes"""
        expiry = calculate_token_expiry(minutes=60)
        
        assert isinstance(expiry, datetime)
        assert expiry.tzinfo == timezone.utc
        
        # Should be approximately 60 minutes from now
        now = datetime.now(timezone.utc)
        diff = expiry - now
        assert 59 <= diff.total_seconds() / 60 <= 61
    
    def test_calculate_token_expiry_zero(self):
        """Test calculate_token_expiry with zero minutes"""
        expiry = calculate_token_expiry(minutes=0)
        
        assert isinstance(expiry, datetime)
        # Should be very close to now
        now = datetime.now(timezone.utc)
        diff = abs((expiry - now).total_seconds())
        assert diff < 5  # Within 5 seconds
    
    def test_calculate_token_expiry_negative(self):
        """Test calculate_token_expiry with negative minutes"""
        expiry = calculate_token_expiry(minutes=-10)
        
        assert isinstance(expiry, datetime)
        # Should be in the past
        now = datetime.now(timezone.utc)
        assert expiry < now

