# TAMS Client Tools

This folder contains client-side tools and scripts for interacting with the TAMS (Time-addressable Media Store) API.

## Contents

### 📁 Upload Scripts
- **`tams_video_upload.py`** - Single media file uploader with CLI interface
- **`batch_media_upload.py`** - Batch uploader for series of media files

### 📚 Documentation
- **`MEDIA_UPLOAD_GUIDE.md`** - Comprehensive guide for media uploads

## ⚠️ Important Notes

### S3 Upload Headers
- **Do NOT add custom headers** to S3 presigned URL uploads
- Custom headers will cause `SignatureDoesNotMatch` errors
- The client automatically handles this by sending minimal headers

### HTTP Library Limitations
- **urllib PUT requests** are not recommended for S3 uploads
- Use the provided uploader scripts which handle S3 compatibility
- The scripts automatically fall back to compatible HTTP methods

## Quick Start

### Single Media Upload
```bash
cd client
python tams_video_upload.py path/to/media_file.mp4
```

### Batch Media Upload
```bash
cd client
python batch_media_upload.py "Series Name" /path/to/media/directory/
```

## Requirements

- Python 3.8+
- TAMS API server running (default: http://localhost:8000)
- Valid S3 credentials configured
- Media files in supported formats (MP4, MOV, AVI, MKV, WMV, FLV)

## Configuration

The client tools use the same configuration as the main TAMS server:
- S3 endpoint and credentials from `config.py`
- API base URL (configurable via command line)
- Presigned URL timeout settings

## Examples

See `MEDIA_UPLOAD_GUIDE.md` for detailed examples and use cases.

## Support

For issues and questions:
- Check the main TAMS API server is running
- Verify S3 credentials and permissions
- Review server logs for detailed error information
- Test individual API endpoints for connectivity
