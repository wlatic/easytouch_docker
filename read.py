import time
import logging
import json
import os
from bluepy.btle import Peripheral, BTLEException

# Configure logging
logging.basicConfig(level=logging.INFO)
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

def parse_zone_data(zone_data):
    zone_status = []
    for zone, data in zone_data.items():
        inside_temp = data[12]
        cooling_set_point = data[2]
        heating_set_point = data[3]
        mode_value = data[10]
        mode = parse_mode(mode_value)
        fan_setting = parse_fan_setting(data[6])
        system_activity = data[15]
        away_status = data[11] == 0  # New: Detect Away status
        
        heating_on = system_activity == 4
        cooling_on = system_activity == 2
        
        zone_info = {
            "Zone": int(zone) + 1,
            "Inside Temperature (°F)": inside_temp,
            "Cooling Set Point (°F)": cooling_set_point,
            "Heating Set Point (°F)": heating_set_point,
            "Mode": mode,
            "Fan Setting": fan_setting,
            "System Activity": parse_system_activity(system_activity),
            "Heating On": heating_on,
            "Cooling On": cooling_on,
            "Away Mode": away_status  # New: Include Away status
        }
        zone_status.append(zone_info)
    return zone_status

def parse_mode(mode_value):
    modes = {0: "Off", 1: "Fan Only", 2: "Cooling", 4: "Heating"}
    return modes.get(mode_value, "Unknown")

def parse_fan_setting(fan_value):
    fan_settings = {1: "Low", 2: "Medium", 3: "High", 128: "Auto"}
    return fan_settings.get(fan_value, "Unknown")

def parse_system_activity(activity_value):
    activities = {0: "Not Active", 2: "Cooling", 4: "Heating"}
    return activities.get(activity_value, "Unknown")

def parse_system_status(prm_data):
    return {
        "Any Zone Active": prm_data[0] == 1,
        "System Status": prm_data[1],
        "Away Mode": prm_data[1] == 75,  # New: Detect Away mode from PRM
        "Unknown Value": prm_data[2],
        "Overall Temperature": prm_data[3]
    }

def main():
    try:
        # Connect to the peripheral
        device = Peripheral(mac_address, addrType='public')
        
        # Perform a single Write Request
        device.writeCharacteristic(write_handle, write_data, withResponse=True)
        time.sleep(1.5)  # Delay after write request
        
        # Read Request
        data = device.readCharacteristic(read_handle)
        
        # Output the complete characteristic value as JSON
        json_data = data.decode('utf-8')
        logger.info("Raw data received from device: %s", json_data)
        data = json.loads(json_data)
        
        # Check if 'Z_sts' key exists
        if "Z_sts" in data:
            zone_data = data["Z_sts"]
            zone_status = parse_zone_data(zone_data)
            
            system_status = parse_system_status(data.get("PRM", [0, 0, 0, 0]))
            
            # Combine zone status and system status
            full_status = {
                "System": system_status,
                "Zones": zone_status
            }
            
            # Save the status to a file
            with open("/usr/src/app/status.json", 'w') as file:
                json.dump(full_status, file, indent=2)
            
            logger.info("Status saved to /usr/src/app/status.json")
        else:
            logger.critical("Key 'Z_sts' not found in data. Received data: %s", data)
        
        # Disconnect from the peripheral
        device.disconnect()
    except BTLEException as e:
        logger.critical("Bluetooth error: %s", e)
    except json.JSONDecodeError as e:
        logger.critical("Failed to decode JSON: %s", e)

if __name__ == "__main__":
    main()
