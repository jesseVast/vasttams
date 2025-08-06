from app.config import Settings

def get_test_settings():
    """
    Return test-specific settings for use in all tests.
    Override with test database, S3, and other config as needed.
    """
    return Settings(
        vast_endpoint="http://100.100.0.1:9090",
        vast_access_key="SRSPW0DQT9T70Y787U68",
        vast_secret_key="WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
        vast_bucket="tamsdb",
        vast_schema="tams",
        s3_endpoint_url="http://100.100.0.2:9090",
        s3_access_key_id="SRSPW0DQT9T70Y787U68",
        s3_secret_access_key="WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
        s3_bucket_name="tamsbucket",
        s3_use_ssl=False,
        debug=True
    ) 