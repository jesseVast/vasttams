# TAMS Sample Applications

This directory contains sample applications demonstrating how to use the TAMS API and client libraries.

## Purpose

These applications serve as:
- **Reference implementations** for common TAMS workflows
- **Learning examples** for developers new to TAMS
- **Integration templates** for building custom TAMS applications
- **Testing utilities** for validating TAMS functionality

## Structure

Each sample application is in its own subdirectory with:
- Application code
- README with usage instructions
- Requirements file (if needed)
- Example configuration (if needed)

## Available Applications

### folder_ingestor

Ingests all files from a folder into TAMS. Each folder becomes one source and one flow. Media files are chunked into time-based segments, non-media files are stored as data files.

**Features:**
- Automatic media detection using ffprobe
- Media chunking into 30-second segments
- Resume support for interrupted ingestions
- Duplicate detection to skip already-processed files
- Progress tracking in source tags

**See:** [folder_ingestor/README.md](folder_ingestor/README.md) for details.

## Usage

Each application directory contains its own README with specific usage instructions.

### Prerequisites

- Python 3.12+
- TAMS server running and accessible
- Valid TAMS credentials (username/password)
- Required dependencies (see individual application READMEs)

### Common Setup

Most applications will require:

```bash
# Install TAMS client library
pip install -e ../src/client

# Or install from requirements
pip install -r requirements.txt

# Set environment variables (if needed)
export TAMS_SERVER_URL=http://localhost:8000
export TAMS_USERNAME=your_username
export TAMS_PASSWORD=your_password
```

## Contributing

When adding a new sample application:

1. Create a new subdirectory with a descriptive name
2. Include a README.md with:
   - Purpose and use case
   - Prerequisites
   - Installation instructions
   - Usage examples
   - Configuration options
3. Include a requirements.txt if external dependencies are needed
4. Add the application to this README's "Available Applications" section
5. Follow Python best practices and include error handling

## Examples to Consider

Potential sample applications:
- **Basic Ingest**: Simple video/audio file upload workflow
- **Batch Processing**: Process multiple files with progress tracking
- **Metadata Management**: Tag and organize media assets
- **Playback Service**: Generate playback URLs and serve media
- **Analytics Dashboard**: Query and visualize TAMS data
- **Webhook Handler**: Process TAMS webhook events
- **Migration Tool**: Migrate data between TAMS instances
- **Backup Utility**: Backup and restore TAMS data
