#!/usr/bin/env python3
"""
Script to fix VastDBManager fixtures in consolidated test files
"""

import re

def fix_vastdbmanager_fixtures():
    """Fix all VastDBManager fixtures in the consolidated test file"""
    
    # Read the file
    with open('mock_tests/test_vastdbmanager_consolidated.py', 'r') as f:
        content = f.read()
    
    # Pattern to match the old fixture format
    old_pattern = r"""    @pytest\.fixture
    def vast_manager\(self\):
        \"\"\"VastDBManager instance\"\"\"
        with patch\('app\.storage\.vastdbmanager\.core\.VastClient'\):
            return VastDBManager\(
                host="test-host",
                port=443,
                username="test-user",
                password="test-pass",
                database="test-db"
            \)"""
    
    # New fixture format
    new_fixture = """    @pytest.fixture
    def vast_manager(self):
        \"\"\"VastDBManager instance\"\"\"
        with patch('app.storage.vastdbmanager.core.vastdb.connect') as mock_vast_connect:
            mock_vast_connect.return_value = MagicMock()
            with patch('app.core.config.get_settings') as mock_settings:
                mock_settings.return_value = MagicMock(
                    vast_access_key="test-key",
                    vast_secret_key="test-secret",
                    vast_bucket="test-bucket",
                    vast_schema="test-schema"
                )
                return VastDBManager("test-endpoint")"""
    
    # Replace all occurrences
    new_content = re.sub(old_pattern, new_fixture, content, flags=re.MULTILINE)
    
    # Write the fixed content back
    with open('mock_tests/test_vastdbmanager_consolidated.py', 'w') as f:
        f.write(new_content)
    
    print("Fixed VastDBManager fixtures in test_vastdbmanager_consolidated.py")

if __name__ == "__main__":
    fix_vastdbmanager_fixtures()
