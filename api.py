from flask import Flask, request, jsonify
import subprocess
import os
import json
import logging

app = Flask(__name__)

# Define the location of the status file
STATUS_FILE = "/usr/src/app/status.json"

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/read', methods=['GET'])
def read_status():
    try:
        # Trigger the read script
        result = subprocess.run(["python3", "/usr/src/app/read.py"], capture_output=True, text=True, check=True)
        app.logger.debug(f"Read script output: {result.stdout}")
        
        # Load the latest status
        try:
            with open(STATUS_FILE, 'r') as file:
                file_content = file.read()
                app.logger.debug(f"File content: {file_content}")
                if not file_content.strip():
                    return jsonify({"error": "Status file is empty"}), 500
                status = json.loads(file_content)
        except json.JSONDecodeError as json_err:
            app.logger.error(f"JSON Decode Error: {str(json_err)}")
            return jsonify({"error": f"Invalid JSON in status file: {str(json_err)}"}), 500
        
        app.logger.debug("Loaded status: %s", status)
        
        # Extract and format the Zones data
        if "Zones" in status and isinstance(status["Zones"], list):
            formatted_zones = []
            for zone in status["Zones"]:
                formatted_zone = {
                    "Zone": zone["Zone"],
                    "Inside Temperature (°F)": zone["Inside Temperature (°F)"],
                    "Cooling Set Point (°F)": zone["Cooling Set Point (°F)"],
                    "Heating Set Point (°F)": zone["Heating Set Point (°F)"],
                    "Mode": zone["Mode"],
                    "Fan Setting": zone["Fan Setting"],
                    "System Activity": zone["System Activity"],
                    "Heating On": zone["Heating On"],
                    "Cooling On": zone["Cooling On"],
                    "Away Mode": zone["Away Mode"]
                }
                # Add system-wide Away Mode if it exists
                if "System" in status and "Away Mode" in status["System"]:
                    formatted_zone["Away Mode"] = status["System"]["Away Mode"]
                formatted_zones.append(formatted_zone)
            return jsonify(formatted_zones)
        else:
            app.logger.error(f"Unexpected data format: {status}")
            return jsonify({"error": "Unexpected data format"}), 500
    
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error running read script: {str(e)}")
        app.logger.error(f"Script output: {e.output}")
        return jsonify({"error": f"Error running read script: {str(e)}"}), 500
    except Exception as e:
        app.logger.error("Error reading status: %s", str(e))
        return jsonify({"error": str(e)}), 500

# ... rest of the code remains the same ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
