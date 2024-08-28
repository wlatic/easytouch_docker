import json
import time
import argparse
import logging
from bluepy.btle import Peripheral, UUID, BTLEException, DefaultDelegate
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class NotificationDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
        self.received_data = []

    def handleNotification(self, cHandle, data):
        try:
            decoded_data = data.decode('utf-8')
            json_data = json.loads(decoded_data)
            logger.info("Received notification: %s", json.dumps(json_data, indent=2))
            self.received_data.append(json_data)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON data: %s", decoded_data)
        except Exception as e:
            logger.error("Error handling notification: %s", str(e))

def send_command(char, command):
    """Sends a command to the BLE device using the characteristic provided."""
    try:
        logger.debug("Sending command: %s", command)
        char.write(command.encode('utf-8'), withResponse=True)
        logger.debug("Command sent successfully")
    except BTLEException as e:
        logger.error("BLE operation failed with error: %s", e)
        raise

def validate_temperature(temp):
    """Validates that the temperature is within the allowed range."""
    if temp < 60 or temp > 80:
        raise ValueError("Temperature must be between 60°F and 80°F")
    return temp

def main(args):
    device_mac = args.mac or os.getenv('MAC_ADDRESS')
    logger.debug("Using MAC address: %s", device_mac)
    if not device_mac:
        logger.error("MAC address is not set. Use --mac option or set MAC_ADDRESS environment variable.")
        raise Exception("MAC address is not set")

    service_uuid = UUID("000000FF-0000-1000-8000-00805f9b34fb")
    char_uuid = UUID("0000EE01-0000-1000-8000-00805f9b34fb")
    p = None
    try:
        logger.debug("Connecting to device with MAC: %s", device_mac)
        p = Peripheral(device_mac)
        p.setDelegate(NotificationDelegate())
        
        svc = p.getServiceByUUID(service_uuid)
        char = next((c for c in svc.getCharacteristics() if c.uuid == char_uuid), None)
        if not char:
            logger.error("Characteristic not found")
            raise Exception("Characteristic not found")

        # Enable notifications
        p.writeCharacteristic(char.valHandle + 1, b"\x01\x00")

        changes = {"zone": args.zone - 1}  # Adjust for 0-based indexing

        if args.power is not None:
            changes["power"] = 1 if args.power == "On" else 0

        if args.mode is not None:
            if args.mode not in [0, 1, 2, 4]:
                logger.error("Invalid mode")
                raise ValueError("Invalid mode")
            changes["mode"] = args.mode

        if args.fan is not None:
            if args.fan not in [1, 2, 3, 128]:
                logger.error("Invalid fan speed")
                raise ValueError("Invalid fan speed")
            if args.mode == 2:  # Cooling mode
                changes["coolFan"] = args.fan
            elif args.mode == 1:  # Fan only mode
                changes["fanOnly"] = min(args.fan, 3)  # Fan only mode doesn't use 128

        if any([args.cool_sp, args.heat_sp, args.dry_sp, args.auto_heat_sp, args.auto_cool_sp]):
            if args.cool_sp: changes["cool_sp"] = validate_temperature(args.cool_sp)
            if args.heat_sp: changes["heat_sp"] = validate_temperature(args.heat_sp)
            if args.dry_sp: changes["dry_sp"] = validate_temperature(args.dry_sp)
            if args.auto_heat_sp: changes["autoHeat_sp"] = validate_temperature(args.auto_heat_sp)
            if args.auto_cool_sp: changes["autoCool_sp"] = validate_temperature(args.auto_cool_sp)

        if changes:
            command = json.dumps({"Type": "Change", "Changes": changes})
            send_command(char, command)
            time.sleep(1)

        # Always request status after changes
        status_command = json.dumps({"Type": "Get Status", "Zone": args.zone - 1, "TM": int(time.time())})
        send_command(char, status_command)

        # Wait for and process notifications
        timeout = 5.0  # 5 seconds timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            if p.waitForNotifications(1.0):
                continue

        logger.info("Command execution completed.")

    except BTLEException as e:
        logger.error("Bluetooth error: %s", e)
        raise
    except ValueError as e:
        logger.error("Value error: %s", e)
        raise
    except Exception as e:
        logger.error("Error: %s", e)
        raise
    finally:
        if p:
            p.disconnect()
            logger.debug("Disconnected from device")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control a BLE HVAC system.")
    parser.add_argument("--mac", help="MAC address of the HVAC device (overrides MAC_ADDRESS environment variable)")
    parser.add_argument("--zone", type=int, required=True, help="Zone number to control (1-based indexing)")
    parser.add_argument("--power", choices=["On", "Off"], help="Power state for the specified zone")
    parser.add_argument("--mode", type=int, choices=[0, 1, 2, 4], help="Mode of operation (0: Off, 1: Fan Only, 2: Cooling, 4: Heating)")
    parser.add_argument("--fan", type=int, choices=[1, 2, 3, 128], help="Fan setting (1: Low, 2: Medium, 3: High, 128: Auto)")
    parser.add_argument("--cool-sp", type=int, help="Cooling setpoint (60-80°F)")
    parser.add_argument("--heat-sp", type=int, help="Heating setpoint (60-80°F)")
    parser.add_argument("--dry-sp", type=int, help="Dry mode setpoint (60-80°F)")
    parser.add_argument("--auto-heat-sp", type=int, help="Auto heat setpoint (60-80°F)")
    parser.add_argument("--auto-cool-sp", type=int, help="Auto cool setpoint (60-80°F)")
    args = parser.parse_args()
    main(args)
