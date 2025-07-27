from pydantic import BaseModel, Field, ConfigDict
# Minimal replacement for BaseSettings for environments where
# pydantic-settings is unavailable.  It simply derives from
# BaseModel without implementing any environment loading.
class BaseSettings(BaseModel):
    model_config = {}

# Provide a computed_field decorator compatible with pydantic v2.
def computed_field(func=None, *, return_type=None):
    def decorator(fn):
        return fn
    return decorator(func) if func else decorator

__all__ = ['BaseSettings', 'Field', 'ConfigDict', 'computed_field']
