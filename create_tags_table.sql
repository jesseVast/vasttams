-- Create tags table for TAMS
-- This table stores tags for both sources and flows in a normalized way

CREATE TABLE IF NOT EXISTS tags (
    id VARCHAR(36) PRIMARY KEY,                    -- UUID4 for the tag record
    entity_type VARCHAR(20) NOT NULL,              -- 'source' or 'flow'
    entity_id VARCHAR(36) NOT NULL,                -- ID of the source or flow
    tag_name VARCHAR(255) NOT NULL,                -- Name of the tag
    tag_value VARCHAR(1000),                       -- Value of the tag (can be NULL)
    created_at TIMESTAMP(9),                       -- When the tag was created
    updated_at TIMESTAMP(9),                       -- When the tag was last updated
    created_date TIMESTAMP(9),                     -- Metadata: creation date
    updated_date TIMESTAMP(9),                     -- Metadata: last update date
    deleted_date TIMESTAMP(9),                     -- Metadata: soft delete date (NULL if not deleted)
    UNIQUE(entity_type, entity_id, tag_name)       -- Prevent duplicate tags per entity
);

-- Create projections for efficient querying
-- Projection 1: By entity_type and entity_id (for getting all tags for an entity)
CREATE PROJECTION IF NOT EXISTS tags_by_entity (
    entity_type,
    entity_id,
    tag_name,
    tag_value,
    created_at,
    updated_at
) AS
SELECT entity_type, entity_id, tag_name, tag_value, created_at, updated_at
FROM tags
ORDER BY entity_type, entity_id, tag_name;

-- Projection 2: By tag_name (for finding all entities with a specific tag)
CREATE PROJECTION IF NOT EXISTS tags_by_name (
    tag_name,
    entity_type,
    entity_id,
    tag_value,
    created_at,
    updated_at
) AS
SELECT tag_name, entity_type, entity_id, tag_value, created_at, updated_at
FROM tags
ORDER BY tag_name, entity_type, entity_id;

-- Projection 3: By entity_id only (for cross-entity tag queries)
CREATE PROJECTION IF NOT EXISTS tags_by_entity_id (
    entity_id,
    entity_type,
    tag_name,
    tag_value,
    created_at,
    updated_at
) AS
SELECT entity_id, entity_type, tag_name, tag_value, created_at, updated_at
FROM tags
ORDER BY entity_id, entity_type, tag_name;
