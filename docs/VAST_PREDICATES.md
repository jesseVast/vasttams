# VAST Predicates Reference

## Overview
VAST database uses ibis syntax for predicates with the `_` object (imported as `from ibis import _`).

## Basic Predicate Syntax

### Equality
```python
from ibis import _

# Column equals value
predicate = (ibis_.column_name == "value")

# Example: id equals specific UUID
predicate = (ibis_.id == "550e8400-e29b-41d4-a716-446655440000")
```

### Comparisons
```python
# Greater than
predicate = (ibis_.column_name > 37)

# Less than or equal
predicate = (ibis_.column_name <= 40)

# Greater than or equal
predicate = (ibis_.column_name >= 28)
```

### List Membership
```python
# Column value is in list
predicate = (ibis_.column_name.isin([45, 51]))
```

### Null/Not Null
```python
# Column is null
predicate = (ibis_.column_name.isnull())

# Column is not null
predicate = (ibis_.column_name.notnull())
```

### Boolean Operations
```python
# Column equals boolean
predicate = (ibis_.deleted == False)

# Column equals None or False (for soft delete)
predicate = (ibis_.deleted.isnull() | (ibis_.deleted == False))
```

## Compound Predicates

### AND Operations
```python
# Multiple conditions with AND
predicate = (ibis_.colx > 37) & (ibis_.coly <= 40)

# Three conditions
predicate = (ibis_.colx >= 28) & (ibis_.coly >= 30) & (ibis_.colz <= 60)
```

### OR Operations
```python
# Multiple conditions with OR
predicate = (ibis_.colx == "value1") | (ibis_.colx == "value2")
```

### Complex Combinations
```python
# Mix of AND/OR
predicate = ((ibis_.colx > 10) & (ibis_.coly < 20)) | (ibis_.colz == "special")
```

## Common Patterns

### Soft Delete Filtering
```python
# Always include this to exclude soft-deleted records
soft_delete_predicate = (ibis_.deleted.isnull() | (ibis_.deleted == False))

# Combine with other predicates
final_predicate = user_predicate & soft_delete_predicate
```

### ID Lookups
```python
# Single ID lookup
predicate = (ibis_.id == record_id)

# Multiple IDs
predicate = (ibis_.id.isin([id1, id2, id3]))
```

### Text Search
```python
# Exact match
predicate = (ibis_.label == "exact_text")

# Pattern matching (if supported)
predicate = (ibis_.description.contains("search_term"))
```

## Implementation Notes

1. **Import**: Always use `from ibis import _`
2. **Consistency**: Use ibis predicates throughout, don't mix with dictionary predicates
3. **Soft Delete**: Always combine user predicates with soft delete predicate using `&`
4. **Performance**: Complex predicates are optimized by VAST internally

## Examples in Code

### Source Lookup
```python
async def get_source(self, source_id: str) -> Optional[Source]:
    from ibis import _
    predicate = (ibis_.id == source_id)
    predicate = self._add_soft_delete_predicate(predicate)
    results = self.db_manager.select('sources', predicate=predicate, output_by_row=True)
```

### Filtered Source List
```python
async def list_sources(self, filters: Optional[Dict[str, Any]] = None) -> List[Source]:
    from ibis import _
    predicate = None
    if filters:
        conditions = []
        if 'label' in filters:
            conditions.append((ibis_.label == filters['label']))
        if 'format' in filters:
            conditions.append((ibis_.format == filters['format']))
        if conditions:
            predicate = conditions[0] if len(conditions) == 1 else conditions[0] & conditions[1]
    
    predicate = self._add_soft_delete_predicate(predicate)
    results = self.db_manager.select('sources', predicate=predicate, output_by_row=True)
```
