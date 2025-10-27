# Schema Organization Summary

## What Was Done

1. **Moved tags schema** from `app/common/storage/schemas.py` to `app/common/tags/schemas.py`
2. **Distributed projection data** to individual schema files in each resource module
3. **Updated schemas registry** to import all schemas and projections from resource modules

## New Structure

```
app/
├── common/
│   ├── storage/
│   │   └── schemas.py          # Pure registry - imports and aggregates
│   └── tags/
│       └── schemas.py          # Tags schema + projections (shared across resources)
├── flows/
│   └── schemas.py              # Flow schemas + projections
├── sources/
│   └── schemas.py              # Source schemas + projections
├── segments/
│   └── schemas.py              # Segment schemas + projections
├── objects/
│   └── schemas.py              # Object schemas + projections
├── service/
│   └── schemas.py              # Service schemas (webhooks, deletion) + projections
└── auth/
    └── schemas.py              # Auth schemas + projections
```

## Benefits

- **Better organization**: Schemas live with their resources
- **Projections co-located**: Schema and projection definitions together
- **Pure registry pattern**: `app/common/storage/schemas.py` now only imports and aggregates
- **Cleaner imports**: Each resource defines its own schemas and projections
- **Easier to maintain**: Changes to a schema don't affect unrelated modules

## Changes Made

### Created
- `app/common/tags/schemas.py` - Tags schema and projections

### Updated
- `app/common/storage/schemas.py` - Now pure registry
- `app/flows/schemas.py` - Added projection functions
- `app/sources/schemas.py` - Added projection functions
- `app/segments/schemas.py` - Added projection functions
- `app/objects/schemas.py` - Added projection functions
- `app/service/schemas.py` - Added projection functions
- `app/auth/schemas.py` - Added projection functions

## Principle

**"Schemas and their projections should live with the resources that own them"**
