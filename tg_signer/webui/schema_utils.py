from typing import Any, Dict


def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean JSON schema to be compatible with nicegui's json_editor.
    Removes 'format' keys which can cause rendering issues.
    """
    if not isinstance(schema, dict):
        return schema

    # Create a copy to avoid modifying the original if needed,
    # though here we are passing a fresh schema so modification in place is also fine.
    # But safe side:
    new_schema = schema.copy()

    if "format" in new_schema:
        del new_schema["format"]

    for key, value in new_schema.items():
        if isinstance(value, dict):
            new_schema[key] = clean_schema(value)
        elif isinstance(value, list):
            new_schema[key] = [
                clean_schema(item) if isinstance(item, dict) else item for item in value
            ]

    return new_schema
