import json
import os
from flask import Flask, jsonify, abort, render_template

# Create the Flask application instance
app = Flask(__name__)

# Define the path to the JSON data file
# It's good practice to place data files in a dedicated directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
JSON_FILE_PATH = os.path.join(DATA_DIR, 'status.json')

# --- Helper Function to Load Data ---
# (fetchDataFromPython function remains the same as before)
def fetchDataFromPython():
    """
    Loads data from a predefined JSON file.
    Handles file creation if it doesn't exist.
    """
    try:
        # Ensure the data directory exists
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            print(f"Created data directory: {DATA_DIR}")

        # Create a sample data.json if it doesn't exist
        if not os.path.exists(JSON_FILE_PATH):
            print(f"Data file not found at {JSON_FILE_PATH}, creating sample file.")
            sample_data = {
                "message": "Sample data - file was just created!",
                "status": "Initial",
                "timestamp": "Never updated"
            }
            with open(JSON_FILE_PATH, 'w') as f:
                json.dump(sample_data, f, indent=4)
            print(f"Created sample data file at: {JSON_FILE_PATH}")
            return sample_data # Return the sample data immediately

        # Read the existing file
        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError: # Should theoretically be handled by creation logic now
        print(f"Error: Data file logic failed for {JSON_FILE_PATH}")
        raise FileNotFoundError(f"Data file not found: {JSON_FILE_PATH}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {JSON_FILE_PATH}: {e}")
        raise json.JSONDecodeError(f"Invalid JSON in file: {JSON_FILE_PATH}", e.doc, e.pos)
    except Exception as e:
        print(f"An unexpected error occurred while reading/writing {JSON_FILE_PATH}: {e}")
        raise Exception(f"Could not read/write data file: {e}")


# --- API Endpoint ---
# (This /api/data endpoint remains the same)
@app.route('/api/data', methods=['GET'])
def get_data():
    """
    API endpoint to fetch data from the JSON file.
    """
    try:
        data = fetchDataFromPython()
        return jsonify(data)
    except FileNotFoundError as e:
        abort(404, description=str(e))
    except json.JSONDecodeError as e:
        abort(500, description=f"Server error: Could not parse data file. {e}")
    except Exception as e:
        abort(500, description=f"Server error: {e}")

# --- MODIFY THIS ROUTE ---
@app.route('/')
def index():
    """
    Serve the main HTML page that will display the data.
    """
    # This tells Flask to find 'index.html' in the 'templates' folder
    return render_template('index.html')

# --- Main Execution Block ---
# (This remains the same)
if __name__ == '__main__':
    try:
        fetchDataFromPython() # Ensure dir/file exists on startup
    except Exception as e:
        print(f"Warning: Could not initialize data file on startup: {e}")

    app.run(debug=True, port=5000)

# --- Sample data/data.json file ---
# You should create a directory named 'data' in the same directory as your python script,
# and inside 'data', create a file named 'data.json' with content like this:
# {
#   "title": "Sample Data",
#   "description": "This is data loaded from a JSON file.",
#   "values": [10, 20, 30, 40],
#   "metadata": {
#     "source": "backend",
#     "version": "1.0"
#   }
# }
# The script will attempt to create this file with default data if it doesn't exist.