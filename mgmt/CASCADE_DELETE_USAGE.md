# Cascade Delete Script - Usage Guide

## Overview
The `cascade_delete.py` script allows you to:
1. Delete sources or flows by ID with full visibility into what will be deleted
2. **Cleanup all empty sources and flows** (sources with no flows, flows with no segments)

It connects to any TAMS server remotely and shows detailed counts before performing the deletion.

## Quick Start

### Basic Usage
```bash
# Delete a source or flow (interactive confirmation)
python mgmt/cascade_delete.py <source-or-flow-id> \
  --server http://localhost:8000 \
  --username admin \
  --password secret

# Skip confirmation (auto-confirm)
python mgmt/cascade_delete.py <source-or-flow-id> \
  --server http://localhost:8000 \
  --username admin \
  --password secret \
  --yes

# Cleanup all empty sources and flows
python mgmt/cascade_delete.py --cleanup-empty \
  --server http://localhost:8000 \
  --username admin \
  --password secret

# Cleanup empty with auto-confirmation
python mgmt/cascade_delete.py --cleanup-empty \
  --server http://localhost:8000 \
  --username admin \
  --password secret \
  --yes
```

### Using Environment Variables
```bash
# Set environment variables
export TAMS_SERVER=http://localhost:8000
export TAMS_USERNAME=admin
export TAMS_PASSWORD=secret

# Now you can omit those parameters
python mgmt/cascade_delete.py <source-or-flow-id>

# Or with auto-confirm
python mgmt/cascade_delete.py <source-or-flow-id> --yes
```

## Features

### 1. Two Operation Modes

**Delete by ID Mode** (default):
- Delete a specific source or flow by ID
- Auto-detects whether the ID is a source or flow
- Tries to fetch as source first
- Falls back to flow if not a source
- Reports error if neither found

**Cleanup Empty Mode** (`--cleanup-empty`):
- Scans all sources and flows in the system
- Finds sources with no flows or all flows empty
- Finds flows with no segments
- Deletes all empty entries
- Shows summary before deletion

### 2. Detailed Analysis
Before deletion, shows:
- **For Sources**:
  - Source details (label, format)
  - Number of flows
  - Per-flow breakdown with segment and object counts
  - Total segments across all flows
  - Total unique objects

- **For Flows**:
  - Flow details (label, format, codec)
  - Number of segments
  - Number of unique objects

### 3. Confirmation Process
Unless `--yes` flag is used, the script:
1. Shows detailed breakdown of what will be deleted
2. Displays warnings about data loss
3. Requires user to type 'yes' to confirm
4. Can be cancelled by typing 'no' or pressing Ctrl+C

### 4. Cleanup Empty Mode Details
- Scans all sources in the system
- Checks each source's flows for segments
- Identifies:
  - Sources with no flows
  - Sources where all flows are empty
  - Flows with no segments (including orphaned flows)
- Deletes empty flows first, then empty sources
- Provides detailed summary of what was found

### 5. Safe Deletion
- Uses official TAMS client library
- Performs proper cascade deletion
- Reports success/failure clearly
- Handles errors gracefully

## Example Output

### Source Deletion
```
🔌 Connecting to TAMS server: http://localhost:8000
✅ Connected successfully

📊 Analyzing source: abc-123
   Label: Test Source
   Format: urn:x-nmos:format:video

🔍 Counting flows and segments...
   Found 2 flow(s)
   - Flow: def-456... (Test Flow 1)
     Segments: 5, Objects: 5
   - Flow: ghi-789... (Test Flow 2)
     Segments: 3, Objects: 3

================================================================================
🚨 WARNING: CASCADE DELETE SOURCE
================================================================================
⚠️  You are about to cascade delete source: abc-123

📊 The following will be PERMANENTLY DELETED:

   Sources:  1
   Flows:    2
   Segments: 8
   Objects:  8

⚠️  This action is IRREVERSIBLE!
⚠️  All data will be PERMANENTLY LOST!

Type 'yes' to confirm deletion: yes
✅ Confirmation received. Proceeding with deletion...

🗑️  Deleting source abc-123...
✅ Successfully deleted source abc-123

✅ Cascade deletion completed successfully!
```

### Flow Deletion
```
🔌 Connecting to TAMS server: http://localhost:8000
✅ Connected successfully

📊 Analyzing flow: def-456
   Label: Test Flow
   Format: urn:x-nmos:format:video
   Codec: video/h264

🔍 Counting segments and objects...
   Segments: 5
   Objects:  5

================================================================================
🚨 WARNING: CASCADE DELETE FLOW
================================================================================
⚠️  You are about to cascade delete flow: def-456

📊 The following will be PERMANENTLY DELETED:

   Flows:    1
   Segments: 5
   Objects:  5

⚠️  This action is IRREVERSIBLE!
⚠️  All data will be PERMANENTLY LOST!

Type 'yes' to confirm deletion: yes
✅ Confirmation received. Proceeding with deletion...

🗑️  Deleting flow def-456...
✅ Successfully deleted flow def-456

✅ Cascade deletion completed successfully!
```

### Cleanup Empty Mode
```
🔌 Connecting to TAMS server: http://localhost:8000
✅ Connected successfully

🔍 Scanning all sources and flows for empty entries...

📋 Found 5 total source(s)
📋 Found 12 total flow(s)

📊 Empty Sources Found:
   - abc-123... (Test Source 1) - no flows
   - def-456... (Test Source 2) - all flows empty

📊 Empty Flows Found:
   - ghi-789... (Empty Flow 1) - Source: Test Source 3
   - jkl-012... (Empty Flow 2) - Source: Test Source 3
   - mno-345... (Orphaned Flow) - Source: (unknown)

================================================================================
🚨 WARNING: CLEANUP EMPTY SOURCES AND FLOWS
================================================================================
⚠️  You are about to delete the following empty entries:

   Sources:  2
   Flows:    3

⚠️  This action is IRREVERSIBLE!
⚠️  All data will be PERMANENTLY LOST!

Type 'yes' to confirm deletion: yes
✅ Confirmation received. Proceeding with deletion...

🗑️  Deleting 3 empty flow(s)...
🗑️  Deleting flow ghi-789...
✅ Successfully deleted flow ghi-789
🗑️  Deleting flow jkl-012...
✅ Successfully deleted flow jkl-012
🗑️  Deleting flow mno-345...
✅ Successfully deleted flow mno-345

🗑️  Deleting 2 empty source(s)...
🗑️  Deleting source abc-123...
✅ Successfully deleted source abc-123
🗑️  Deleting source def-456...
✅ Successfully deleted source def-456

================================================================================
📊 CLEANUP SUMMARY
================================================================================
✅ Successfully deleted sources: 2
✅ Successfully deleted flows: 3

✅ Cleanup completed successfully!
```

## Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `id` | - | Source or Flow ID to delete (optional if `--cleanup-empty` used) | - |
| `--server` | - | TAMS server URL | `$TAMS_SERVER` or `http://localhost:8000` |
| `--username` | - | Username for authentication | `$TAMS_USERNAME` |
| `--password` | - | Password for authentication | `$TAMS_PASSWORD` |
| `--yes` | `-y` | Skip confirmation prompt | `false` |
| `--cleanup-empty` | - | Find and delete all empty sources and flows | `false` |
| `--help` | `-h` | Show help message | - |

## Error Handling

### Connection Errors
```
❌ Connection error: Failed to connect to server
```
- Check server URL is correct
- Verify server is running
- Check network connectivity

### Authentication Errors
```
❌ Authentication failed: Invalid credentials
```
- Verify username and password
- Check user has proper permissions

### Not Found
```
❌ Error: ID 'abc-123' not found as source or flow
```
- Verify the ID exists
- Check for typos in the ID

## Safety Warnings

⚠️ **WARNING: This script performs CASCADE DELETION**
- All dependent resources will be permanently deleted
- Source deletion → deletes flows, segments, and objects
- Flow deletion → deletes segments and objects
- This action is IRREVERSIBLE
- Always verify the ID before confirming deletion

⚠️ **Best Practices**
1. Always review the analysis output carefully
2. Double-check the ID before confirming
3. Use `--yes` flag only in automated scripts
4. Keep backups before deleting production data
5. Test in development environment first

## Advanced Usage

### Scripting
```bash
#!/bin/bash
# Delete multiple test sources
for id in source-1 source-2 source-3; do
  python mgmt/cascade_delete.py $id \
    --server http://localhost:8000 \
    --username admin \
    --password secret \
    --yes
done

# Cleanup all empty sources and flows periodically
python mgmt/cascade_delete.py --cleanup-empty \
  --server http://localhost:8000 \
  --username admin \
  --password secret \
  --yes
```

### Docker Container
```bash
# Execute from outside container
docker exec -it tams-api python /app/mgmt/cascade_delete.py <id> \
  --server http://localhost:8000 \
  --username admin \
  --password secret

# With auto-confirm
docker exec -it tams-api python /app/mgmt/cascade_delete.py <id> \
  --server http://localhost:8000 \
  --username admin \
  --password secret \
  --yes
```

### Environment File
```bash
# Create .env file
cat > .env.tams << EOF
TAMS_SERVER=http://localhost:8000
TAMS_USERNAME=admin
TAMS_PASSWORD=secret
EOF

# Source it
source .env.tams

# Run script
python mgmt/cascade_delete.py <id>
```

## Troubleshooting

### Import Errors
If you get import errors, make sure the TAMS client is installed:
```bash
pip install -e src/client/
```

### Permission Errors
If you get permission errors, check:
1. User has proper role (admin or editor)
2. Authentication credentials are correct
3. Server is accessible from your location

### Network Timeouts
If the connection times out:
1. Check server is running and accessible
2. Verify firewall rules
3. Try increasing timeout in client connection

## See Also
- `mgmt/README.md` - Overview of all management scripts
- `mgmt/delete_sources_by_label_filter.py` - Bulk deletion by label
- `src/client/README.md` - TAMS client library documentation

