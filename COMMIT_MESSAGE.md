fix(database): remove artifacts referencing deleted is_active and version fields

After simplifying the database schema by removing versioning fields (is_active, version) from ReadModelPosition,
several code artifacts remained that caused runtime errors.

### Fixed Issues:
- repositories.py: Removed references to ReadModelPosition.is_active (lines 282, 712) 
- repositories.py: Removed references to ReadModelDeal.is_active (lines 625, 732)
- Deleted obsolete read_model_position_sync.py with versioning logic
- Fixed debug scripts: view_positions_table.py, export_positions_excel.py

### Testing Results:
- ✅ All integration tests pass (84 insertions + 84 deletions)
- ✅ No runtime errors
- ✅ System operates stably with simplified schema

### Performance Impact:
- No performance degradation
- Simplified codebase easier to maintain
- Full compatibility with SimplePositionSync logic

Fixes: AttributeError 'ReadModelPosition' has no attribute 'is_active'

BREAKING CHANGE: None - internal refactoring only
