import time
import logging
import json
import os
from bluepy.btle import Peripheral, BTLEException

# Configure logging
logging.basicConfig(level=logging.CRITICAL)  # Set logging to critical to suppress logs
logger = logging.getLogger(__name__)

# Define the peripheral MAC address
mac_address = os.getenv("MAC_ADDRESS", "24:DC:C3:21:05:EE")

# Define the characteristic handle for writing and reading
write_handle = 0x002a
read_handle = 0x002c

# Define the write data as a single payload
write_data = (
    b'{"Type":"Get Status","Zone":0,"TM":"1715308063"}'
)

def parse_status_data(status_data):
    zone_status = []
    for zone, data in status_data.items():
        inside_temp = data[3]
        target_temp = data[11]
        mode = parse_mode(data[9])
        heating_on = mode == "Heating" and target_temp > inside_temp
        cooling_on = mode == "Cooling" and target_temp < inside_temp
        
        if mode == "Off":
            heating_on = False
            cooling_on = False
        
        zone_info = {
            "Zone": int(zone),
            "Inside Temperature (°F)": inside_temp,
            "Cooling Set Point (°F)": data[7],
            "Heating Set Point (°F)": data[8],
            "Mode": mode,
            "Fan Setting": parse_fan_setting(data[10]),
            "Target Temperature (°F)": target_temp,
            "Heating On": heating_on,
            "Cooling On": cooling_on
        }
        zone_status.append(zone_info)
    return zone_status

def parse_mode(mode_value):
    modes = {0: "Off", 1: "Heating", 3: "Fan Only", 4: "Cooling"}
    return modes.get(mode_value, "Unknown")

def parse_fan_setting(fan_value):
    fan_settings = {0: "Low", 1: "Medium", 2: "High", 3: "Auto"}
    return fan_settings.get(fan_value, "Unknown")

def main():
    try:
        # Connect to the peripheral
        device = Peripheral(mac_address)

        # Perform a single Write Request
        device.writeCharacteristic(write_handle, write_data, withResponse=True)

        time.sleep(1.5)  # Delay after write request

        # Read Request
        data = device.readCharacteristic(read_handle)

        # Output the complete characteristic value as JSON
        json_data = data.decode('utf-8')
        data = json.loads(json_data)
        status_data = data["status"]
        zone_status = parse_status_data(status_data)

        # Save the status of each zone to a file
        with open("/usr/src/app/status.json", 'w') as file:
            json.dump(zone_status, file)

        # Disconnect from the peripheral
        device.disconnect()

    except BTLEException as e:
        logger.critical("Bluetooth error: %s", e)

if __name__ == "__main__":
    main()
