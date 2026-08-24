from __future__ import annotations

import re
from typing import Any


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "object": (dict,),
    "array": (list,),
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "null": (type(None),),
}


def validate_instance(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate the JSON Schema subset used by AI-BENCH-001.

    The repository deliberately keeps the benchmark runner dependency-free.
    Unsupported schema keywords are rejected by the package validator, so this
    function remains deterministic in CI and local/offline environments.
    """

    errors: list[str] = []
    declared_type = schema.get("type")
    if declared_type:
        expected = _JSON_TYPES.get(declared_type)
        if expected is None:
            return [f"{path}: unsupported schema type {declared_type!r}"]
        type_ok = isinstance(instance, expected)
        if declared_type in {"number", "integer"} and isinstance(instance, bool):
            type_ok = False
        if not type_ok:
            return [f"{path}: expected {declared_type}, got {type(instance).__name__}"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value is not in enum")

    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}.{key}: required property is missing")
        for key, value in instance.items():
            if key in properties:
                errors.extend(validate_instance(value, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: additional property is not allowed")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            errors.append(f"{path}: expected at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            errors.append(f"{path}: string is shorter than {schema['minLength']}")
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            errors.append(f"{path}: string is longer than {schema['maxLength']}")
        if "pattern" in schema and re.search(str(schema["pattern"]), instance) is None:
            errors.append(f"{path}: string does not match required pattern")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")

    return errors


def find_unsupported_keywords(schema: Any, path: str = "$") -> list[str]:
    supported = {
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "pattern",
    }
    errors: list[str] = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key not in supported:
                errors.append(f"{path}: unsupported schema keyword {key!r}")
            if key == "properties" and isinstance(value, dict):
                for property_name, property_schema in value.items():
                    errors.extend(find_unsupported_keywords(property_schema, f"{path}.properties.{property_name}"))
            elif key == "items":
                errors.extend(find_unsupported_keywords(value, f"{path}.items"))
    return errors
