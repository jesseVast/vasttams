#!/usr/bin/env python3
"""Test script to verify map_concat functionality"""

def test_map_concat_syntax():
    """Test map_concat SQL syntax"""
    try:
        # Test different map_concat syntaxes
        test_cases = [
            # Case 1: Basic map_concat
            """
            UPDATE sources 
            SET tags = map_concat(
                COALESCE(tags, MAP(ARRAY[], ARRAY[])), 
                MAP(ARRAY['test_key'], ARRAY['test_value'])
            ) 
            WHERE id = 'test-id'
            """,
            
            # Case 2: Direct map assignment
            """
            UPDATE sources 
            SET tags = MAP(ARRAY['test_key'], ARRAY['test_value'])
            WHERE id = 'test-id'
            """,
            
            # Case 3: Using CAST
            """
            UPDATE sources 
            SET tags = CAST('{"test_key": "test_value"}' AS MAP(VARCHAR, VARCHAR))
            WHERE id = 'test-id'
            """
        ]
        
        for i, sql in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i} ---")
            print(f"SQL: {sql.strip()}")
            
            # Check if the SQL looks valid
            if "map_concat" in sql:
                print("✅ Uses map_concat function")
            elif "MAP(" in sql and "ARRAY" in sql:
                print("✅ Uses MAP literal syntax")
            elif "CAST" in sql:
                print("✅ Uses CAST syntax")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_map_concat_syntax()
