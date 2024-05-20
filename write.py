import json
import time
import argparse
import logging
from bluepy.btle import Peripheral, UUID, BTLEException
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def send_command(char, command):
    """Sends a command to the BLE device using the characteristic provided."""
    try:
        logger.debug("Sending command: %s", command)
        char.write(command, withResponse=True)
        logger.debug("Command sent successfully")
    except BTLEException as e:
        logger.error("BLE operation failed with error: %s", e)
        raise

def main(args):
    device_mac = os.getenv('MAC_ADDRESS')
    logger.debug("MAC_ADDRESS environment variable: %s", device_mac)
    if not device_mac:
        logger.error("MAC address is not set in the environment variables")
        raise Exception("MAC address is not set in the environment variables")

    service_uuid = UUID("000000FF-0000-1000-8000-00805f9b34fb")
    char_uuid = UUID("0000EE01-0000-1000-8000-00805f9b34fb")
    p = None
    try:
        logger.debug("Connecting to device with MAC: %s", device_mac)
        p = Peripheral(device_mac)
        svc = p.getServiceByUUID(service_uuid)
        char = next((c for c in svc.getCharacteristics() if c.uuid == char_uuid), None)
        if not char:
            logger.error("Characteristic not found")
            raise Exception("Characteristic not found")

        if args.zone is None:
            logger.error("Zone number is required")
            raise Exception("Zone number is required")

        if args.power:
            if args.power not in ["On", "Off"]:
                logger.error("Invalid power state")
                raise Exception("Invalid power state")
            command = {"Type": "Change", "Changes": {"zone": args.zone, "power": args.power}}
            if args.power == "Off":
                command["Changes"]["mode"] = 0  # Include mode: 0 for power off
            send_command(char, json.dumps(command).encode('utf-8'))
            time.sleep(5)
        
        if args.mode is not None:
            if args.mode not in [0, 1, 3, 4]:
                logger.error("Invalid mode")
                raise Exception("Invalid mode")
            send_command(char, json.dumps({"Type": "Change", "Changes": {"zone": args.zone, "mode": args.mode}}).encode('utf-8'))
            time.sleep(5)
        
        if args.temperature is not None:
            if args.temperature < 60 or args.temperature > 80:
                logger.error("Invalid temperature")
                raise Exception("Invalid temperature")
            
            # Ensure we have the mode argument to determine the correct set point
            if args.mode == 1:  # Heating mode
                set_point = "heat_sp"
            elif args.mode == 4:  # Cooling mode
                set_point = "cool_sp"
            else:
                # If mode is not explicitly provided, default to current mode (which should be handled by the API)
                raise Exception("Temperature set point requires explicit mode to determine heat_sp or cool_sp")
            
            send_command(char, json.dumps({"Type": "Change", "Changes": {"zone": args.zone, set_point: args.temperature}}).encode('utf-8'))
            time.sleep(5)
        
        if args.fan is not None:
            if args.fan not in [0, 1, 2, 3]:
                logger.error("Invalid fan speed")
                raise Exception("Invalid fan speed")
            send_command(char, json.dumps({"Type": "Change", "Changes": {"zone": args.zone, "fan": args.fan}}).encode('utf-8'))
            time.sleep(5)

    except BTLEException as e:
        logger.error("Bluetooth error: %s", e)
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
    parser.add_argument("--zone", type=int, help="Zone number to control")
    parser.add_argument("--power", choices=["On", "Off"], help="Power state")
    parser.add_argument("--mode", type=int, choices=[0, 1, 3, 4], help="Mode of operation")
    parser.add_argument("--temperature", type=int, help="Temperature setting")
    parser.add_argument("--fan", type=int, choices=[0, 1, 2, 3], help="Fan setting")
    args = parser.parse_args()
    main(args)
