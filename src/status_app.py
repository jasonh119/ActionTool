import json
import os
from flask import Flask, jsonify, abort

# Create the Flask application instance
app = Flask(__name__)

# Define the path to the JSON data file
# It's good practice to place data files in a dedicated directory
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
JSON_FILE_PATH = os.path.join(DATA_DIR, 'status.json')

# --- Helper Function to Load Data ---
def fetchDataFromPython():
    """
    Loads data from a predefined JSON file.

    Returns:
        dict: The data loaded from the JSON file.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        Exception: For other potential file reading errors.
    """
    try:
        # Ensure the data directory exists
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            # Create a sample data.json if it doesn't exist
            sample_data = {
                "message": "Hello from the backend!",
                "items": ["item1", "item2", "item3"],
                "timestamp": "2023-01-01T12:00:00Z"
            }
            with open(JSON_FILE_PATH, 'w') as f:
                json.dump(sample_data, f, indent=4)
            print(f"Created sample data directory and file at: {JSON_FILE_PATH}")

        elif not os.path.exists(JSON_FILE_PATH):
             # Create a sample data.json if it doesn't exist but dir does
            sample_data = {
                "message": "Hello from the backend!",
                "items": ["item1", "item2", "item3"],
                "timestamp": "2023-01-01T12:00:00Z"
            }
            with open(JSON_FILE_PATH, 'w') as f:
                json.dump(sample_data, f, indent=4)
            print(f"Created sample data file at: {JSON_FILE_PATH}")


        with open(JSON_FILE_PATH, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: Data file not found at {JSON_FILE_PATH}")
        # In a real app, you might return default data or raise a specific error
        raise FileNotFoundError(f"Data file not found: {JSON_FILE_PATH}")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in {JSON_FILE_PATH}: {e}")
        raise json.JSONDecodeError(f"Invalid JSON in file: {JSON_FILE_PATH}", e.doc, e.pos)
    except Exception as e:
        print(f"An unexpected error occurred while reading {JSON_FILE_PATH}: {e}")
        raise Exception(f"Could not read data file: {e}")


# --- API Endpoint ---
@app.route('/api/data', methods=['GET'])
def get_data():
    """
    API endpoint to fetch data from the JSON file.
    """
    try:
        data = fetchDataFromPython()
        return jsonify(data)
    except FileNotFoundError as e:
        # Return a 404 Not Found error if the file doesn't exist
        abort(404, description=str(e))
    except json.JSONDecodeError as e:
        # Return a 500 Internal Server Error for invalid JSON
        abort(500, description=f"Server error: Could not parse data file. {e}")
    except Exception as e:
        # Return a generic 500 error for other issues
        abort(500, description=f"Server error: {e}")

# --- Basic Route for Testing ---
@app.route('/')
def index():
    """
    A simple index route to confirm the server is running.
    """
    return "Backend server is running. Access data at /api/data"

# --- Main Execution Block ---
if __name__ == '__main__':
    # Ensure the data directory and a sample file exist on startup
    try:
        fetchDataFromPython() # This call ensures dir/file creation if needed
    except Exception as e:
        print(f"Warning: Could not initialize data file on startup: {e}")

    # Run the Flask development server
    # Debug=True enables auto-reloading and provides detailed error pages
    # In production, use a proper WSGI server like Gunicorn or uWSGI
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