# CESMII SM Profile Validator

Validate JSON payloads against [CESMII Smart Manufacturing Profile](https://www.cesmii.org/technology/sm-profiles/) definitions.

## Why This Exists

CESMII SM Profiles use JSON-LD for semantic interoperability, but JSON-LD doesn't provide runtime validation. This library fills that gap by validating payloads against profile definitions, checking:

- Required fields and structure
- OPC UA data types (Int32, Int64, Double, String, DateTime, etc.)
- Nested profile references (e.g., WorkOrder containing FeedIngredients)
- Array fields with unlimited length

## Installation

```bash
# From source
pip install -e .

# Or just copy cesmii_validator/ to your project
```

## Quick Start

```python
from cesmii_validator import validate_payload, load_profile

# Load profiles
workorder_profile = load_profile("smprofiles/WorkOrderV1.jsonld")
feedingredient_profile = load_profile("smprofiles/FeedIngredientV1.jsonld")

# Your payload from MQTT, API, etc.
payload = {
    "$namespace": "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1",
    "WorkOrderID": "e68308bc-4f85-46f8-8778-73efe5119096",
    "WorkOrderNumber": 100026,
    "TimeZone": {"offset": -360, "daylightSavingInOffset": False},
    # ... rest of payload
}

# Validate with nested profile support
result = validate_payload(
    payload=payload,
    profile=workorder_profile,
    referenced_profiles={
        "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1": feedingredient_profile,
    }
)

if result.valid:
    print("Payload is valid!")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## How It Works

### JSON-LD vs NodeSet2.xml

CESMII SM Profiles can be exported in two formats. This validator uses **JSON-LD only**:

| File | Format | Used By Validator |
|------|--------|-------------------|
| `WorkOrderV1.jsonld` | JSON-LD | **Yes** - parsed for field names and types |
| `WorkOrderV1.NodeSet2.xml` | OPC UA XML | No - not used |

Both formats describe the same profile (same fields, same types), just in different serializations for different ecosystems:

```
WorkOrderV1 Profile
       │
       ├── WorkOrderV1.NodeSet2.xml  →  OPC UA servers/clients
       │
       └── WorkOrderV1.jsonld        →  JSON/MQTT/Web ecosystem ← validator uses this
```

### Profile Parsing

When you load a profile, the validator extracts field definitions from two sections:

```json
// @context - maps field names to OPC UA types
"@context": {
    "WorkOrderNumber": {
        "@id": "WorkOrderV1:WorkOrderNumber",
        "@type": "opc:Int32"
    }
}

// cesmii:attributes - detailed field definitions
"cesmii:attributes": [
    {
        "cesmii:browseName": "WorkOrderNumber",
        "cesmii:dataType": {
            "@id": "opc:Int32"
        }
    },
    {
        "cesmii:browseName": "FeedIngredients",
        "cesmii:isArray": true,
        "cesmii:dataType": {
            "cesmii:profileReference": "...FeedIngredientV1.jsonld"
        }
    }
]
```

The validator builds a lookup dict: `{"WorkOrderNumber": field_def, "TimeZone": field_def, ...}`

### Type Validation

For each field in the payload, it checks the value against OPC UA type rules:

```python
OPC_TYPE_VALIDATORS = {
    "opc:Int32":   lambda v: isinstance(v, int) and -2147483648 <= v <= 2147483647,
    "opc:Double":  lambda v: isinstance(v, (int, float)),
    "opc:String":  lambda v: isinstance(v, str),
    "opc:UtcTime": lambda v: isinstance(v, str) and v.endswith("Z"),
    ...
}
```

### Nested Validation Flow

```
validate(WorkOrder payload)
    │
    ├── Check WorkOrderNumber → opc:Int32 → valid?
    ├── Check TimeZone → opc:TimeZoneDataType → validate structure
    │       ├── Check offset → opc:Int16 → valid?
    │       └── Check daylightSavingInOffset → opc:Boolean → valid?
    ├── Check StartTimeUTC → opc:UtcTime → ends with Z?
    │
    └── Check FeedIngredients → isArray=true, has profileReference
            │
            └── For each item[i]:
                    │
                    └── Create new ProfileValidator(FeedIngredientV1)
                            ├── Check ProductID → opc:String
                            ├── Check ProductNumber → opc:Int64
                            ├── Check Quantity → opc:Double
                            └── ...
```

### Error Collection

Errors are collected with their path for easy debugging:

```python
@dataclass
class ValidationError:
    path: str       # "FeedIngredients[0].ProductNumber"
    message: str    # "Invalid type"
    expected: str   # "integer (64-bit)"
    actual: str     # "str"
```

### Visual Summary

```
┌─────────────────────────────────────────────────────────┐
│  Payload (JSON)          Profile (JSON-LD)              │
│  ─────────────────       ──────────────────             │
│  {                       cesmii:attributes: [           │
│    "WorkOrderNumber": 100   {browseName: "WorkOrderNumber",
│         │                    dataType: "opc:Int32"}     │
│         │                         │                     │
│         └─────────────────────────┘                     │
│                    ↓                                    │
│         ┌─────────────────────┐                         │
│         │  Type Validator     │                         │
│         │  Is 100 a valid     │                         │
│         │  Int32? → YES ✓     │                         │
│         └─────────────────────┘                         │
└─────────────────────────────────────────────────────────┘
```

The key insight is that CESMII profiles already contain type information in `cesmii:dataType` - the validator just reads it and applies the corresponding Python type check.

## Loading Profiles

Profiles can be loaded from local files or URLs:

```python
from cesmii_validator import load_profile

# From local file
profile = load_profile("smprofiles/WorkOrderV1.jsonld")

# From URL
profile = load_profile(
    "https://raw.githubusercontent.com/eukodyne/cesmii/main/smprofiles/WorkOrderV1.jsonld"
)
```

## Supported OPC UA Data Types

| OPC UA Type | Python Type | Validation |
|-------------|-------------|------------|
| Boolean | `bool` | Must be `True` or `False` |
| Int16 | `int` | -32,768 to 32,767 |
| Int32 | `int` | -2,147,483,648 to 2,147,483,647 |
| Int64 | `int` | Full 64-bit range |
| UInt16 | `int` | 0 to 65,535 |
| UInt32 | `int` | 0 to 4,294,967,295 |
| UInt64 | `int` | 0 to 18,446,744,073,709,551,615 |
| Float | `float` | Any float/int |
| Double | `float` | Any float/int |
| String | `str` | Any string |
| DateTime | `str` | ISO 8601 format |
| UtcTime | `str` | ISO 8601 ending with `Z` |
| Guid | `str` | UUID format |
| TimeZoneDataType | `dict` | Object with `offset` (Int16) and `daylightSavingInOffset` (Boolean) |

## Nested Profile Validation

When a profile references another profile (like WorkOrderV1 referencing FeedIngredientV1), provide the referenced profiles:

```python
result = validate_payload(
    payload=payload,
    profile=workorder_profile,
    referenced_profiles={
        "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1": feedingredient_profile,
    }
)
```

The validator will automatically validate each item in the `FeedIngredients` array against the FeedIngredientV1 profile.

## Validation Result

```python
result = validate_payload(payload, profile)

result.valid      # bool: True if payload is valid
result.errors     # list[ValidationError]: List of validation errors
result.warnings   # list[str]: Non-fatal warnings

for error in result.errors:
    print(error.path)      # Field path, e.g., "FeedIngredients[0].Quantity"
    print(error.message)   # Error description
    print(error.expected)  # Expected type/value
    print(error.actual)    # Actual type/value
```

## Example Output

```
CESMII SM Profile Validator - Work Order Example
==================================================

Loading WorkOrderV1 profile from: smprofiles/WorkOrderV1.jsonld
Loading FeedIngredientV1 profile from: smprofiles/FeedIngredientV1.jsonld
Loading payload from: examples/sample_payload.json

Validating payload...
--------------------------------------------------
✓ Payload is VALID
```

With errors:
```
✗ Payload is INVALID (3 errors)

Errors:
  - WorkOrderNumber: Invalid type (expected: integer (-2147483648 to 2147483647), got: str)
  - TimeZone.offset: Invalid type (expected: integer (-32768 to 32767), got: int)
  - StartTimeUTC: Invalid type (expected: ISO 8601 UTC time (ending with Z), got: str)
```

## Running the Example

```bash
cd cesmii-profile-validator
python examples/validate_workorder.py
```

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Integration Ideas

- **MQTT Subscriber**: Validate incoming messages before processing
- **API Gateway**: Validate payloads before forwarding to backend services
- **Data Pipeline**: Filter invalid records before storage
- **Testing**: Verify your publisher generates valid payloads

## License

Apache License 2.0

## References

- [CESMII SM Profiles](https://www.cesmii.org/technology/sm-profiles/)
- [CESMII Profile Designer](https://profiledesigner.cesmii.net/)
- [OPC UA Data Types](https://reference.opcfoundation.org/v105/Core/docs/Part6/)
- [JSON-LD Specification](https://www.w3.org/TR/json-ld11/)
