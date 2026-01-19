# Validation Ideas for CESMII SM Profile Payloads

JSON-LD is primarily a semantic linking format, not a validation schema like JSON Schema. The `@context` in the profile defines how terms map to URIs for interoperability, but doesn't provide built-in runtime validation.

## Option 1: Convert to JSON Schema

Generate a JSON Schema from the profile's `cesmii:attributes` and validate with standard tools.

```bash
pip install jsonschema
```

```python
from jsonschema import validate, ValidationError

# Would need to generate schema from WorkOrderV1.jsonld
schema = {...}  # Generated JSON Schema

try:
    validate(instance=payload, schema=schema)
    print("Valid")
except ValidationError as e:
    print(f"Invalid: {e.message}")
```

**Pros**: Industry-standard validation, rich error messages, many library options
**Cons**: Requires schema generation/maintenance step

## Option 2: Use pyld for JSON-LD Expansion

Expand documents using JSON-LD processing and verify structure.

```bash
pip install pyld
```

```python
from pyld import jsonld

# Expand the payload with context
expanded = jsonld.expand(payload, {'expandContext': context})

# Check for expected properties in expanded form
```

**Pros**: Native JSON-LD processing, semantic verification
**Cons**: Doesn't validate data types, more about structure than values

## Option 3: Custom Validator

Parse the `cesmii:attributes` from the profile and validate payloads against them directly.

```python
def validate_against_profile(payload: dict, profile: dict) -> list[str]:
    errors = []

    # Extract expected attributes from profile
    attributes = profile.get('cesmii:attributes', [])

    for attr in attributes:
        field_name = attr.get('cesmii:browseName')
        data_type = attr.get('cesmii:dataType', {}).get('@id')

        if field_name not in payload:
            errors.append(f"Missing required field: {field_name}")
            continue

        # Validate type based on OPC UA data type
        value = payload[field_name]
        if not validate_opc_type(value, data_type):
            errors.append(f"Invalid type for {field_name}: expected {data_type}")

    return errors

def validate_opc_type(value, opc_type: str) -> bool:
    """Validate value against OPC UA data type."""
    type_validators = {
        'opc:String': lambda v: isinstance(v, str),
        'opc:Int32': lambda v: isinstance(v, int) and -2147483648 <= v <= 2147483647,
        'opc:Int64': lambda v: isinstance(v, int),
        'opc:Double': lambda v: isinstance(v, (int, float)),
        'opc:Boolean': lambda v: isinstance(v, bool),
        'opc:DateTime': lambda v: isinstance(v, str),  # Could add ISO 8601 validation
        'opc:UtcTime': lambda v: isinstance(v, str),
    }
    validator = type_validators.get(opc_type, lambda v: True)
    return validator(value)
```

**Pros**: Tailored to CESMII format, uses OPC UA type definitions directly, no schema conversion needed
**Cons**: Custom code to maintain, need to handle nested types (TimeZoneDataType, FeedIngredients array)

## Recommendation

Option 3 (Custom Validator) is most appropriate for this project because:
- Directly uses the existing profile structure
- Can validate against OPC UA data types
- No additional schema files to maintain
- Can be extended to validate nested structures (FeedIngredientV1)
