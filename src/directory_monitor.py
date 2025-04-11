import configparser
import logging
import os
import time
from pathlib import Path
import sys
import json

# --- Constants ---
CONFIG_FILE = 'config.ini'
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
ACK_PLAN_TEMPLATE = """
Acknowledgement:
Received and read file: {original_filename}
Timestamp: {timestamp}

Execution Plan:
1. Validate the instructions provided in '{original_filename}'.
2. Allocate necessary resources for the task.
3. Execute the steps outlined in the instructions.
4. Verify the successful completion of the task.
5. Report status/results as required.
"""

# --- Global State ---
# Keep track of files already seen/processed to avoid reprocessing
processed_files = set()
status_data = {
    "last_check_time": None,
    "last_files_found": 0,
    "total_processed_count": 0,
    "monitoring_active": False,
    "error": None
}
status_file_path = Path('status.json') # Default path

# --- Logging Setup ---
def setup_logging():
    """Configures basic logging for the application."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[
        logging.StreamHandler(sys.stdout)
        # Optionally add FileHandler here:
        # logging.FileHandler("monitor.log")
    ])
    logging.info("Logging initialized.")

# --- Configuration Loading ---
def load_config(config_file_path):
    """Loads configuration from the specified INI file."""
    config = configparser.ConfigParser()
    if not config_file_path.is_file():
        logging.error(f"Configuration file not found: {config_file_path}")
        print(f"Error: Configuration file '{config_file_path}' not found.")
        print("Please create it with [Monitor] section including 'Directory' and 'PollIntervalSeconds'.")
        sys.exit(1) # Exit if config is missing

    try:
        config.read(config_file_path)
        monitor_dir_str = config.get('Monitor', 'ToDoDirectory', fallback=None)
        poll_interval_str = config.get('Monitor', 'PollIntervalSeconds', fallback='900') # Default 15 mins
        ack_suffix = config.get('Monitor', 'AckSuffix', fallback='_ack.txt')
        status_file_str = config.get('Monitor', 'StatusFile', fallback='status.json') # Get status file path

        if not monitor_dir_str:
            logging.error("Configuration error: 'Directory' not set in [{}]".format('Monitor'))
            print("Error: 'Directory' must be specified in config file.")
            sys.exit(1)

        monitor_dir = Path(monitor_dir_str)

        # Validate directory exists
        if not monitor_dir.is_dir():
             logging.warning(f"Monitor directory does not exist: {monitor_dir}. Attempting to create it.")
             try:
                 monitor_dir.mkdir(parents=True, exist_ok=True)
                 logging.info(f"Successfully created monitor directory: {monitor_dir}")
             except OSError as e:
                 logging.error(f"Failed to create monitor directory {monitor_dir}: {e}")
                 print(f"Error: Could not create monitor directory '{monitor_dir}'. Please check permissions.")
                 sys.exit(1)

        # Validate poll interval
        try:
            poll_interval = int(poll_interval_str)
            if poll_interval <= 0:
                raise ValueError("Poll interval must be positive.")
        except ValueError:
            logging.error(f"Invalid 'PollIntervalSeconds': {poll_interval_str}. Using default 900 seconds.")
            poll_interval = 900

        # Validate status file path
        global status_file_path # Use global variable
        status_file_path = Path(status_file_str)
        # Ensure parent directory exists for status file
        try:
            status_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logging.warning(f"Could not create parent directory for status file {status_file_path}: {e}")
            # Continue, maybe writing to current dir is fine, or save_status will fail later

        logging.info(f"Configuration loaded: MonitorDir='{monitor_dir}', PollInterval={poll_interval}s, AckSuffix='{ack_suffix}', StatusFile='{status_file_path}'")
        return monitor_dir, poll_interval, ack_suffix

    except configparser.Error as e:
        logging.error(f"Error reading configuration file {config_file_path}: {e}")
        print(f"Error parsing configuration file '{config_file_path}'. Check its format.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred during configuration loading: {e}")
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


# --- Status Saving ---
def save_status():
    """Saves the current status_data dictionary to the JSON file."""
    global status_data, status_file_path
    try:
        with status_file_path.open('w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4)
        logging.debug(f"Status saved to {status_file_path}")
    except IOError as e:
        logging.error(f"Failed to save status to {status_file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error saving status: {e}")


# --- File Processing ---
def process_file(file_path: Path, ack_suffix: str):
    """Reads the instruction file and creates an acknowledgment file."""
    logging.info(f"Processing new file: {file_path.name}")
    try:
        # 1. Read the instruction file content
        with file_path.open('r', encoding='utf-8') as f:
            content = f.read()
            logging.info(f"Successfully read content from {file_path.name}")
            # You could potentially parse or use 'content' here if needed

        # 2. Create the acknowledgment file path
        ack_filename = f"{file_path.stem}{ack_suffix}"
        ack_filepath = file_path.with_name(ack_filename)

        # 3. Prepare acknowledgment content
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        ack_content = ACK_PLAN_TEMPLATE.format(
            original_filename=file_path.name,
            timestamp=timestamp
        )

        # 4. Write the acknowledgment file
        with ack_filepath.open('w', encoding='utf-8') as f_ack:
            f_ack.write(ack_content)
        logging.info(f"Created acknowledgment file: {ack_filepath.name}")

    except FileNotFoundError:
        logging.error(f"File not found during processing (it might have been deleted): {file_path}")
    except IOError as e:
        logging.error(f"IOError processing file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing file {file_path}: {e}")


# --- Directory Monitoring ---
def check_directory(monitor_dir: Path, ack_suffix: str):
    """Checks the directory for new .txt files and processes them."""
    global status_data, processed_files # Add status_data
    logging.debug(f"Checking directory: {monitor_dir}")
    files_processed_this_run = 0
    status_data['last_check_time'] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    status_data['error'] = None # Clear previous error

    try:
        current_files = set(monitor_dir.glob('*.txt')) # Get all .txt files
        # Determine new files (present now but not in processed_files set)
        new_files = current_files - processed_files

        for file_path in new_files:
            # Ignore already processed files (safeguard) and ack files
            if file_path in processed_files or file_path.name.endswith(ack_suffix):
                # Add ack files to processed set so they aren't re-checked constantly
                processed_files.add(file_path)
                continue

            # Process the new instruction file
            process_file(file_path, ack_suffix)
            processed_files.add(file_path) # Mark as processed
            files_processed_this_run += 1
            status_data['total_processed_count'] += 1 # Increment total count

        # Optional: Clean up processed_files set if files are deleted
        # This prevents the set from growing indefinitely if files are removed
        # from the directory externally.
        deleted_files = processed_files - current_files
        if deleted_files:
            logging.debug(f"Removing {len(deleted_files)} deleted files from processed set.")
            processed_files.difference_update(deleted_files)


    except FileNotFoundError:
        logging.error(f"Monitor directory not found during check: {monitor_dir}. It might have been deleted.")
        # Depending on requirements, might want to exit or keep retrying
    except OSError as e:
        logging.error(f"OS error checking directory {monitor_dir}: {e}")
        status_data['error'] = f"OS error checking directory: {e}"
    except Exception as e:
        logging.error(f"Unexpected error checking directory {monitor_dir}: {e}")
        status_data['error'] = f"Unexpected error checking directory: {e}"

    if files_processed_this_run > 0:
        logging.info(f"Processed {files_processed_this_run} new file(s).")
    else:
        logging.info("No new instruction files found.")

    status_data['last_files_found'] = files_processed_this_run
    save_status() # Save status after check


# --- Main Application Logic ---
def main():
    """Main function to run the directory monitor."""
    setup_logging()
    config_path = Path(CONFIG_FILE)
    monitor_dir, poll_interval, ack_suffix = load_config(config_path)

    global status_data # Use global
    status_data['monitoring_active'] = True
    status_data['error'] = None
    save_status() # Save initial status

    logging.info("--- Directory Monitor Started ---")
    logging.info(f"Monitoring: {monitor_dir}")
    logging.info(f"Checking every {poll_interval} seconds.")

    # Initial scan to populate processed_files with existing files
    # so they are not processed on the first real check loop
    try:
        logging.info("Performing initial scan of the directory...")
        initial_files = set(monitor_dir.glob('*.txt'))
        processed_files.update(initial_files)
        logging.info(f"Initial scan complete. Found {len(initial_files)} existing .txt files (will be ignored).")
    except Exception as e:
         logging.error(f"Error during initial scan of {monitor_dir}: {e}")
         # Decide if fatal or not, here we continue but log the error

    # Main monitoring loop
    try:
        while True:
            check_directory(monitor_dir, ack_suffix)
            logging.info(f"Sleeping for {poll_interval} seconds...")
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        logging.info("--- Directory Monitor Stopped (Keyboard Interrupt) ---")
        status_data['monitoring_active'] = False
        status_data['last_check_time'] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        status_data['error'] = "Stopped by user (KeyboardInterrupt)"
        save_status() # Save final status on exit
    except Exception as e:
        logging.error(f"An unexpected error caused the monitor to stop: {e}")
        status_data['monitoring_active'] = False
        status_data['last_check_time'] = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        status_data['error'] = f"Fatal error: {e}"
        save_status() # Save final status on error
        print(f"Monitor stopped due to unexpected error: {e}")
    finally:
        logging.info("Application shutdown.")

if __name__ == "__main__":
    main()