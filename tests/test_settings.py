from app.config import Settings

def get_test_settings():
    """
    Return test-specific settings for use in all tests.
    Override with test database, S3, and other config as needed.
    """
    return Settings(
        vast_endpoint="http://172.200.204.6",
        vast_access_key="SRSPW0DQT9T70Y787U68",
        vast_secret_key="WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
        vast_bucket="jthaloor-db",
        vast_schema="bbctams",
        s3_endpoint_url="http://172.200.204.6",
        s3_access_key_id="SRSPW0DQT9T70Y787U68",
        s3_secret_access_key="WkKLxvG7YkAdSMuHjFsZG5/BhDk9Ou7BS1mDQGnr",
        s3_bucket_name="jthaloor-s3",
        s3_use_ssl=False,
        debug=True
    ) 