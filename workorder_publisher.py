#!/usr/bin/env python3
"""
CESMII Work Order Publisher Demo Application

This application demonstrates the use of CESMII Smart Manufacturing (SM) Profiles
by publishing work orders to an MQTT broker (UNS). The work orders conform to the
WorkOrderV1 SM Profile using CESMII's $namespace format for profile identification.

Author: Demo Application
Version: 1.1.0
"""

import json
import random
import string
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

import paho.mqtt.client as mqtt
import pytz


# =============================================================================
# CESMII SM Profile Namespaces
# =============================================================================

WORKORDER_NAMESPACE = "https://www.github.com/eukodyne/cesmii/smprofiles/WorkOrderV1"
FEEDINGREDIENT_NAMESPACE = "https://www.github.com/eukodyne/cesmii/smprofiles/FeedIngredientV1"


# =============================================================================
# Demo Products Definition
# =============================================================================

class FeedIngredient:
    """Represents a feed ingredient with mix proportion."""

    def __init__(self, product_id: str, product_number: int, product_name: str, mix_proportion: float):
        self.product_id = product_id
        self.product_number = product_number
        self.product_name = product_name
        self.mix_proportion = mix_proportion  # As decimal (0.10 = 10%)


class DemoProduct:
    """Represents a demo product with its feed ingredients."""

    def __init__(self, product_id: str, product_number: int, product_name: str, ingredients: list[FeedIngredient]):
        self.product_id = product_id
        self.product_number = product_number
        self.product_name = product_name
        self.ingredients = ingredients


def create_demo_products() -> list[DemoProduct]:
    """Create the lookup list of demo products with their feed ingredients."""

    # Product A with 3 ingredients (10%, 30%, 60%)
    product_a = DemoProduct(
        product_id=str(uuid.uuid4()),
        product_number=2221,
        product_name="Product A",
        ingredients=[
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=2001,
                product_name="Product A1",
                mix_proportion=0.10
            ),
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=2002,
                product_name="Product A2",
                mix_proportion=0.30
            ),
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=2003,
                product_name="Product A3",
                mix_proportion=0.60
            ),
        ]
    )

    # Product B with 2 ingredients (30%, 70%)
    product_b = DemoProduct(
        product_id=str(uuid.uuid4()),
        product_number=4450,
        product_name="Product B",
        ingredients=[
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=4001,
                product_name="Product B1",
                mix_proportion=0.30
            ),
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=4002,
                product_name="Product B2",
                mix_proportion=0.70
            ),
        ]
    )

    # Product C with 2 ingredients (50%, 50%)
    product_c = DemoProduct(
        product_id=str(uuid.uuid4()),
        product_number=3170,
        product_name="Product C",
        ingredients=[
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=3001,
                product_name="Product C1",
                mix_proportion=0.50
            ),
            FeedIngredient(
                product_id=str(uuid.uuid4()),
                product_number=3002,
                product_name="Product C2",
                mix_proportion=0.50
            ),
        ]
    )

    return [product_a, product_b, product_c]


# =============================================================================
# Work Order Generation
# =============================================================================

class WorkOrderGenerator:
    """Generates work orders conforming to the WorkOrderV1 SM Profile."""

    def __init__(self, demo_products: list[DemoProduct]):
        self.demo_products = demo_products
        self.work_order_counter = 100000  # Starting work order number
        self.central_tz = pytz.timezone('America/Chicago')  # US Central Time

    def _generate_random_lot(self, length: int = 6) -> str:
        """Generate a random alphanumeric lot number in all caps."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def _get_quantity_divisible_by_6(self, min_val: int = 12, max_val: int = 120) -> int:
        """Generate a random quantity between min and max that is divisible by 6."""
        # Get all multiples of 6 in the range
        multiples = [x for x in range(min_val, max_val + 1) if x % 6 == 0]
        return random.choice(multiples)

    def _get_timezone_data(self) -> dict[str, Any]:
        """
        Get TimeZoneDataType structure for US Central Time.

        TimeZoneDataType (OPC UA) structure:
        - offset: Int16 - Time difference from UTC in minutes
        - daylightSavingInOffset: Boolean - If TRUE, DST is in effect
        """
        now = datetime.now(self.central_tz)

        # Get UTC offset in minutes
        utc_offset = now.utcoffset()
        offset_minutes = int(utc_offset.total_seconds() / 60) if utc_offset else -360

        # Check if DST is in effect
        dst = now.dst()
        dst_in_effect = dst is not None and dst.total_seconds() > 0

        return {
            "offset": offset_minutes,
            "daylightSavingInOffset": dst_in_effect
        }

    def generate_work_order(self) -> dict[str, Any]:
        """
        Generate a new work order with all required fields.

        Returns a dictionary conforming to the WorkOrderV1 SM Profile with
        $namespace reference for profile identification (CESMII standard format).
        """
        # Select random product
        tmp_product = random.choice(self.demo_products)

        # Calculate times
        now_utc = datetime.now(pytz.UTC)
        now_local = now_utc.astimezone(self.central_tz)
        end_utc = now_utc + timedelta(hours=8)
        end_local = now_local + timedelta(hours=8)

        # Generate quantity and weight
        tmp_quantity = float(self._get_quantity_divisible_by_6())
        tmp_weight = tmp_quantity * 2.0

        # Generate lot number with format LOT-YYYYMMDD-HHmmss
        lot_number = f"LOT-{now_local.strftime('%Y%m%d-%H%M%S')}"

        # Generate feed ingredients with calculated quantities and weights
        feed_ingredients = []
        for ingredient in tmp_product.ingredients:
            ingredient_quantity = tmp_quantity * ingredient.mix_proportion
            ingredient_weight = tmp_weight * ingredient.mix_proportion

            feed_ingredients.append({
                "$namespace": FEEDINGREDIENT_NAMESPACE,
                "ProductID": ingredient.product_id,
                "ProductNumber": ingredient.product_number,
                "ProductName": ingredient.product_name,
                "LotNumber": self._generate_random_lot(),
                "UnitOfMeasure": "CS",
                "Quantity": ingredient_quantity,
                "WeightUnitOfMeasure": "lb",
                "Weight": ingredient_weight
            })

        # Build work order with CESMII $namespace format
        work_order = {
            "$namespace": WORKORDER_NAMESPACE,
            "$comment": "Work order conforming to WorkOrderV1 SM Profile",
            "WorkOrderID": str(uuid.uuid4()),
            "WorkOrderNumber": self.work_order_counter,
            "TimeZone": self._get_timezone_data(),
            "StartTimeLocal": now_local.isoformat(),
            "StartTimeUTC": now_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "EndTimeLocal": end_local.isoformat(),
            "EndTimeUTC": end_utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "ProductID": tmp_product.product_id,
            "ProductNumber": tmp_product.product_number,
            "ProductName": tmp_product.product_name,
            "LotNumber": lot_number,
            "UnitOfMeasure": "CS",
            "Quantity": tmp_quantity,
            "WeightUnitOfMeasure": "lb",
            "Weight": tmp_weight,
            "FeedIngredients": feed_ingredients
        }

        # Increment work order counter for next order
        self.work_order_counter += 1

        return work_order


# =============================================================================
# MQTT Publisher
# =============================================================================

class MQTTWorkOrderPublisher:
    """Publishes work orders to MQTT broker as retained messages."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.client: mqtt.Client | None = None
        self.connected = False

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, reason_code: int, properties: Any = None) -> None:
        """Callback when connected to MQTT broker."""
        if reason_code == 0:
            self.connected = True
            print(f"Connected to MQTT broker at {self.config['mqtt-endpoint']['host']}:{self.config['mqtt-endpoint']['port']}")
        else:
            print(f"Failed to connect to MQTT broker. Reason code: {reason_code}")

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: int, properties: Any = None) -> None:
        """Callback when disconnected from MQTT broker."""
        self.connected = False
        print(f"Disconnected from MQTT broker. Reason code: {reason_code}")

    def _on_publish(self, client: mqtt.Client, userdata: Any, mid: int, reason_code: int = 0, properties: Any = None) -> None:
        """Callback when message is published."""
        print(f"Message published successfully. Message ID: {mid}")

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        try:
            # Create MQTT client with protocol version 5
            self.client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"workorder-publisher-{uuid.uuid4().hex[:8]}",
                # protocol=mqtt.MQTTv5
            )

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish

            # Set credentials if provided
            endpoint = self.config['mqtt-endpoint']
            if endpoint.get('username') and endpoint.get('password'):
                self.client.username_pw_set(endpoint['username'], endpoint['password'])

            # Connect to broker
            self.client.connect(
                host=endpoint['host'],
                port=endpoint['port'],
                keepalive=60
            )

            # Start network loop
            self.client.loop_start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            return self.connected

        except Exception as e:
            print(f"Error connecting to MQTT broker: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False

    def publish_work_order(self, work_order: dict[str, Any]) -> bool:
        """
        Publish a work order to the configured MQTT topic as a retained message.

        Args:
            work_order: The work order dictionary to publish

        Returns:
            True if published successfully, False otherwise
        """
        if not self.client or not self.connected:
            print("Not connected to MQTT broker")
            return False

        try:
            topic = self.config['mqtt-publish-topic']
            payload = json.dumps(work_order, indent=2)

            # Publish as retained message
            result = self.client.publish(
                topic=topic,
                payload=payload,
                qos=1,
                retain=True
            )

            # Wait for publish to complete
            result.wait_for_publish(timeout=10)

            if result.is_published():
                print(f"Work order {work_order['WorkOrderNumber']} published to topic: {topic}")
                return True
            else:
                print(f"Failed to publish work order {work_order['WorkOrderNumber']}")
                return False

        except Exception as e:
            print(f"Error publishing work order: {e}")
            return False


# =============================================================================
# Main Application
# =============================================================================

def load_config(config_path: str = "config.json") -> dict[str, Any]:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {e}")
        raise


def main() -> None:
    """Main entry point for the work order publisher application."""
    print("=" * 60)
    print("CESMII Work Order Publisher Demo")
    print("=" * 60)
    print()
    print("This application demonstrates CESMII Smart Manufacturing Profiles")
    print("by publishing work orders to an MQTT broker every 10 seconds.")
    print()
    print(f"Work Order Namespace: {WORKORDER_NAMESPACE}")
    print(f"Feed Ingredient Namespace: {FEEDINGREDIENT_NAMESPACE}")
    print()

    # Load configuration
    print("Loading configuration...")
    config = load_config()
    print(f"MQTT Broker: {config['mqtt-endpoint']['host']}:{config['mqtt-endpoint']['port']}")
    print(f"Publish Topic: {config['mqtt-publish-topic']}")
    print()

    # Create demo products
    print("Initializing demo products...")
    demo_products = create_demo_products()
    for product in demo_products:
        print(f"  - {product.product_name} (#{product.product_number}): {len(product.ingredients)} ingredients")
    print()

    # Create work order generator
    generator = WorkOrderGenerator(demo_products)

    # Create MQTT publisher
    publisher = MQTTWorkOrderPublisher(config)

    # Connect to broker
    print("Connecting to MQTT broker...")
    if not publisher.connect():
        print("Failed to connect to MQTT broker. Exiting.")
        return
    print()

    try:
        # Main loop - publish work order every 10 seconds
        print("Starting work order publishing loop (every 10 seconds)...")
        print("Press Ctrl+C to stop.")
        print()

        while True:
            # Generate work order
            work_order = generator.generate_work_order()

            print("-" * 40)
            print(f"Generated Work Order #{work_order['WorkOrderNumber']}")
            print(f"  Product: {work_order['ProductName']} (#{work_order['ProductNumber']})")
            print(f"  Lot: {work_order['LotNumber']}")
            print(f"  Quantity: {work_order['Quantity']} {work_order['UnitOfMeasure']}")
            print(f"  Weight: {work_order['Weight']} {work_order['WeightUnitOfMeasure']}")
            print(f"  Ingredients: {len(work_order['FeedIngredients'])}")
            print(f"  Start (Local): {work_order['StartTimeLocal']}")
            print(f"  End (Local): {work_order['EndTimeLocal']}")

            # Publish work order
            publisher.publish_work_order(work_order)
            print()

            # Wait for 10 seconds before next work order
            print("Waiting 10 seconds until next work order...")
            time.sleep(10)

    except KeyboardInterrupt:
        print()
        print("Shutting down...")
    finally:
        publisher.disconnect()
        print("Disconnected from MQTT broker.")
        print("Goodbye!")


if __name__ == "__main__":
    main()
