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
        subprocess.run(["python3", "/usr/src/app/read.py"], check=True)
        # Load the latest status
        with open(STATUS_FILE, 'r') as file:
            status = json.load(file)
        return jsonify(status)
    except Exception as e:
        app.logger.error("Error reading status: %s", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/write', methods=['POST'])
def write_command():
    try:
        data = request.json
        app.logger.debug("Received data: %s", data)
        
        command = ["python3", "/usr/src/app/write.py"]

        if 'zone' in data:
            command.extend(["--zone", str(data['zone'])])
        if 'power' in data:
            command.extend(["--power", data['power']])
        if 'mode' in data:
            command.extend(["--mode", str(data['mode'])])
        if 'temperature' in data:
            command.extend(["--temperature", str(data['temperature'])])
        if 'fan' in data:
            command.extend(["--fan", str(data['fan'])])

        app.logger.debug("Executing command: %s", command)

        # Execute the write command
        subprocess.run(command, check=True)
        
        return jsonify({"status": "Command sent successfully"})
    except subprocess.CalledProcessError as e:
        app.logger.error("Subprocess error: %s", str(e))
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error("Error writing command: %s", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
