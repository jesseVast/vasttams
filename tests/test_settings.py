from app.core.config import Settings, get_settings

def get_test_settings():
    """
    Return test-specific settings for use in all tests.
    Uses the main config settings but allows for test-specific overrides.
    """
    # Get the main settings from config
    settings = get_settings()
    
    # Return the settings as-is (using config.py values)
    # If you need test-specific overrides, you can modify specific values here
    return settings 