# CESMII Smart Manufacturing Profiles Demo

This project demonstrates the use of **CESMII Smart Manufacturing (SM) Profiles** for publishing structured manufacturing data to an MQTT broker (Unified Namespace - UNS). The demo application generates and publishes work orders that conform to custom SM Profile definitions in JSON-LD format.

## Purpose

The purpose of this demo is to demonstrate how CESMII SM Profiles can be used as "information contracts" to standardize data exchange in manufacturing environments. SM Profiles provide:

- **Type definitions** based on OPC UA Information Models
- **Semantic interoperability** through JSON-LD linked data
- **Protocol independence** - profiles work with MQTT, OPC UA, REST, and other protocols
- **Data validation** - consumers can validate incoming data against profile schemas

## What Are CESMII SM Profiles?

CESMII SM Profiles are standardized type definitions for smart manufacturing that enable data contracts independent of communication protocols or infrastructure. They start as OPC UA Information Model Type definitions and can be extended for various use cases.

Key benefits:
- **Standardization**: Common data structures across industry
- **Interoperability**: Different systems can understand the same data
- **Traceability**: Data carries its schema reference for validation
- **Flexibility**: Profiles can be composed and extended

For more information, see:
- [CESMII SM Profiles Overview](https://www.cesmii.org/technology/sm-profiles/)
- [CESMII Profile Designer](https://profiledesigner.cesmii.net/)
- [ProveIt SM Profiles Guide](https://github.com/cesmii/ProveIt-SMProfiles)

## Project Structure

```
cesmii/
├── config.json                     # MQTT broker configuration (template)
├── Dockerfile                      # Docker container definition
├── requirements.txt                # Python dependencies
├── workorder_publisher.py          # Main application
├── smprofiles/
│   ├── FeedIngredientV1.jsonld     # Feed ingredient SM Profile
│   ├── FeedIngredientV1.NodeSet2.xml # OPC UA NodeSet for feed ingredient
│   ├── WorkOrderV1.jsonld          # Work order SM Profile
│   └── WorkOrderV1.NodeSet2.xml    # OPC UA NodeSet for work order
└── README.md                       # This file
```

## SM Profile Definitions

### WorkOrderV1

The work order profile (`smprofiles/WorkOrderV1.jsonld`) defines the structure for manufacturing work orders with the following attributes:

| Attribute | OPC UA Type | Description |
|-----------|-------------|-------------|
| WorkOrderID | String | Unique identifier (GUID) |
| WorkOrderNumber | Int32 | Sequential work order number |
| TimeZone | TimeZoneDataType | Time zone with offset and DST flag |
| StartTimeLocal | DateTime | Start time in local timezone |
| StartTimeUTC | UtcTime | Start time in UTC |
| EndTimeLocal | DateTime | End time in local timezone |
| EndTimeUTC | UtcTime | End time in UTC |
| ProductID | String | Product identifier |
| ProductNumber | Int64 | Numeric product code |
| ProductName | String | Human-readable product name |
| LotNumber | String | Production lot identifier |
| UnitOfMeasure | String | Unit for quantity (e.g., "CS") |
| Quantity | Double | Amount to produce |
| WeightUnitOfMeasure | String | Unit for weight (e.g., "lb") |
| Weight | Double | Total weight |
| FeedIngredients | FeedIngredientV1[] | List of required ingredients |

### FeedIngredientV1

The feed ingredient profile (`smprofiles/FeedIngredientV1.jsonld`) defines ingredient data:

| Attribute | OPC UA Type | Description |
|-----------|-------------|-------------|
| ProductID | String | Ingredient identifier |
| ProductNumber | Int64 | Numeric ingredient code |
| ProductName | String | Ingredient name |
| LotNumber | String | Ingredient lot number |
| UnitOfMeasure | String | Unit for quantity |
| Quantity | Double | Amount required |
| WeightUnitOfMeasure | String | Unit for weight |
| Weight | Double | Weight of ingredient |

## Demo Products

The application includes three demo products with predefined feed ingredients:

### Product A (ProductNumber: 2221)
- Product A1: 10% mix proportion
- Product A2: 30% mix proportion
- Product A3: 60% mix proportion

### Product B (ProductNumber: 4450)
- Product B1: 30% mix proportion
- Product B2: 70% mix proportion

### Product C (ProductNumber: 3170)
- Product C1: 50% mix proportion
- Product C2: 50% mix proportion

## Work Order Generation Logic

Every hour, the application generates a new work order:

1. **WorkOrderID**: New UUID
2. **WorkOrderNumber**: Starts at 100000, increments by 1
3. **TimeZone**: US Central Time (America/Chicago)
4. **StartTimeLocal**: Current time in Central Time
5. **StartTimeUTC**: Current UTC time
6. **EndTimeLocal/UTC**: Start time + 8 hours
7. **Product**: Random selection from demo products
8. **LotNumber**: Format "LOT-YYYYMMDD-HHmmss"
9. **Quantity**: Random 12-120, divisible by 6
10. **Weight**: Quantity x 2
11. **FeedIngredients**: Based on product recipe with proportional quantities

## Prerequisites

- Python 3.12 or higher
- Access to an MQTT broker (e.g., Mosquitto, HiveMQ, EMQX)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/eukodyne/cesmii.git
   cd cesmii
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config.json` to configure your MQTT broker connection:

```json
{
  "mqtt-endpoint": {
    "host": "localhost",
    "port": 1883,
    "username": "",
    "password": ""
  },
  "mqtt-publish-topic": "uns/workorders/demo"
}
```

| Property | Description |
|----------|-------------|
| host | MQTT broker hostname or IP address |
| port | MQTT broker port (default: 1883) |
| username | MQTT username (leave empty if not required) |
| password | MQTT password (leave empty if not required) |
| mqtt-publish-topic | Topic where work orders are published |

## Running the Application

```bash
python workorder_publisher.py
```

The application will:
1. Connect to the MQTT broker
2. Generate a work order immediately
3. Publish the work order as a retained message
4. Wait 1 hour and repeat

Press `Ctrl+C` to stop the application.

## Docker Deployment

The application can be deployed as a Docker container on a Linux server.

### Prerequisites

- Docker installed on the target Linux server
- Git installed on the target Linux server

### Deployment Steps

1. **Clone the repository on the Linux server:**
   ```bash
   git clone https://github.com/eukodyne/cesmii.git
   cd cesmii
   ```

2. **Create a local configuration directory:**
   ```bash
   sudo mkdir -p /opt/cesmii
   ```

3. **Copy and edit the configuration file with your MQTT credentials:**
   ```bash
   sudo cp config.json /opt/cesmii/config.json
   sudo nano /opt/cesmii/config.json
   ```

   Update the file with your actual MQTT broker settings:
   ```json
   {
     "mqtt-endpoint": {
       "host": "your-mqtt-broker.example.com",
       "port": 1883,
       "username": "your-username",
       "password": "your-password"
     },
     "mqtt-publish-topic": "Enterprise/YourCompany/WorkOrders"
   }
   ```

4. **Build the Docker image:**
   ```bash
   docker build -t workorder-publisher .
   ```

5. **Run the container with the local config mounted:**
   ```bash
   docker run -d --name workorder-publisher \
     --restart unless-stopped \
     -v /opt/cesmii/config.json:/app/config.json:ro \
     workorder-publisher
   ```

   The `-v` flag mounts your local config file into the container (`:ro` = read-only).
   The `--restart unless-stopped` ensures the container restarts automatically after server reboots.

### Container Management

```bash
# View container logs
docker logs -f workorder-publisher

# Stop the container
docker stop workorder-publisher

# Start the container
docker start workorder-publisher

# Remove the container
docker rm workorder-publisher

# Rebuild after pulling updates
git pull
docker build -t workorder-publisher .
docker stop workorder-publisher && docker rm workorder-publisher
docker run -d --name workorder-publisher \
  --restart unless-stopped \
  -v /opt/cesmii/config.json:/app/config.json:ro \
  workorder-publisher
```

## Example Work Order Payload

```json
{
  "@context": {
    "@version": 1.1,
    "cesmii": "https://profiles.cesmii.org/",
    "opc": "http://opcfoundation.org/UA/",
    "WorkOrderV1": "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1#",
    "FeedIngredientV1": "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1#",
    "profileDefinition": {
      "@id": "cesmii:profileDefinition",
      "@type": "@id"
    }
  },
  "@type": "WorkOrderV1",
  "profileDefinition": "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1.jsonld",
  "WorkOrderID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "WorkOrderNumber": 100001,
  "TimeZone": {
    "offset": -360,
    "daylightSavingInOffset": false
  },
  "StartTimeLocal": "2024-01-15T08:00:00-06:00",
  "StartTimeUTC": "2024-01-15T14:00:00.000000Z",
  "EndTimeLocal": "2024-01-15T16:00:00-06:00",
  "EndTimeUTC": "2024-01-15T22:00:00.000000Z",
  "ProductID": "product-uuid-here",
  "ProductNumber": 2221,
  "ProductName": "Product A",
  "LotNumber": "LOT-20240115-080000",
  "UnitOfMeasure": "CS",
  "Quantity": 60.0,
  "WeightUnitOfMeasure": "lb",
  "Weight": 120.0,
  "FeedIngredients": [
    {
      "@type": "FeedIngredientV1",
      "ProductID": "ingredient-uuid-1",
      "ProductNumber": 2001,
      "ProductName": "Product A1",
      "LotNumber": "ABC123",
      "UnitOfMeasure": "CS",
      "Quantity": 6.0,
      "WeightUnitOfMeasure": "lb",
      "Weight": 12.0
    }
  ]
}
```

## JSON-LD and Profile References

Each published work order includes a JSON-LD `@context` that:
- Defines namespace prefixes for OPC UA and CESMII
- Maps field names to profile attribute URIs
- Includes a `profileDefinition` link to the full profile schema

This allows consuming applications to:
- Validate incoming data against the profile definition
- Understand data semantics without prior coordination
- Maintain interoperability across different systems

## OPC UA Data Types

The profiles use standard OPC UA data types from namespace `http://opcfoundation.org/UA/`:

| Type | NodeId | Usage |
|------|--------|-------|
| Boolean | i=1 | TimeZoneDataType.daylightSavingInOffset |
| Int16 | i=4 | TimeZoneDataType.offset |
| Int32 | i=6 | WorkOrderNumber |
| Int64 | i=8 | ProductNumber |
| Double | i=11 | Quantity, Weight |
| String | i=12 | IDs, names, lot numbers |
| DateTime | i=13 | Local timestamps |
| UtcTime | i=294 | UTC timestamps |
| TimeZoneDataType | i=8912 | Time zone structure |

## References

- [CESMII - The Smart Manufacturing Institute](https://www.cesmii.org/)
- [CESMII SM Profiles](https://www.cesmii.org/technology/sm-profiles/)
- [OPC UA Information Model (Part 5)](https://reference.opcfoundation.org/v105/Core/docs/Part5/)
- [OPC UA JSON Encoding (Part 6)](https://reference.opcfoundation.org/v105/Core/docs/Part6/5.4/)
- [JSON-LD Specification](https://www.w3.org/TR/json-ld11/)
- [Paho MQTT Python Client](https://eclipse.dev/paho/files/paho.mqtt.python/html/)

## License

This demo is provided for educational purposes to demonstrate CESMII SM Profile usage.
