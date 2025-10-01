# scripts/shared_state.py
import json
import os
import threading
import time
import logging

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(__file__), 'state.json')
_lock = threading.Lock()

def initialize_state(instance_ids: list):
    """Creates the initial state file at the start of a run."""
    with _lock:
        logger.info(f"Initializing shared state for {len(instance_ids)} instances.")
        initial_data = {
            "race_winners": [],
            "instances": {
                instance_id: {"status": "starting", "gate": 0} for instance_id in instance_ids
            }
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(initial_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to initialize state file: {e}")

def _read_state():
    """Reads the current state from the JSON file. Not thread-safe by itself."""
    try:
        if not os.path.exists(STATE_FILE):
            return None
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def _write_state(data: dict):
    """Writes data to the JSON file. Not thread-safe by itself."""
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_instance_gate(instance_id: str, gate_number: int, status: str = "ok"):
    """Thread-safely updates the gate and status of a specific browser instance."""
    with _lock:
        for _ in range(5):
            state = _read_state()
            if state and instance_id in state["instances"]:
                state["instances"][instance_id]["gate"] = gate_number
                state["instances"][instance_id]["status"] = status
                _write_state(state)
                logger.debug(f"State updated for {instance_id}: gate={gate_number}, status={status}")
                return
            time.sleep(0.1)
        logger.error(f"Failed to update state for {instance_id} after multiple retries.")


def wait_at_gate(instance_id: str, gate_number: int, all_instance_ids: list, timeout: int = 120):
    """
    Causes a thread to wait until all other active instances have reached the same gate.
    """
    logger.info(f"[{instance_id}] Arrived at Gate #{gate_number}. Waiting for others...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        with _lock:
            state = _read_state()
            if not state:
                time.sleep(1)
                continue
            
            active_instances = [inst_id for inst_id, data in state["instances"].items() if data["status"] not in ["failed", "loser", "critical_failure"]]
            if not active_instances: return True # All other browsers failed, so we can proceed
            
            all_at_gate = all(state["instances"][inst_id]["gate"] >= gate_number for inst_id in active_instances)

            if all_at_gate:
                logger.info(f"[{instance_id}] All active instances have reached Gate #{gate_number}. Proceeding.")
                return True
        time.sleep(1)
    
    logger.error(f"[{instance_id}] Timed out waiting at Gate #{gate_number}. Aborting.")
    return False

def get_instances_to_close_by_number(num_to_close: int) -> list:
    """
    Returns a list of the highest-numbered active instances to close.
    """
    with _lock:
        state = _read_state()
        if not state or num_to_close == 0:
            return []
        
        active_instances = [inst_id for inst_id, data in state["instances"].items() if data["status"] not in ["failed", "loser", "critical_failure"]]
        
        # Sort by instance number (e.g., Browser-10 > Browser-1) in descending order
        active_instances.sort(key=lambda x: int(x.split('-')[1]), reverse=True)
        
        # Return the top N instances from the sorted list
        return active_instances[:num_to_close]

def attempt_to_win_race(instance_id: str, max_winners: int) -> bool:
    """
    Thread-safely tries to become a winner in the race condition.
    """
    with _lock:
        state = _read_state()
        if not state:
            return False
            
        if len(state["race_winners"]) < max_winners:
            state["race_winners"].append(instance_id)
            _write_state(state)
            logger.info(f"[{instance_id}] WON THE RACE! Winners: {len(state['race_winners'])}/{max_winners}.")
            return True
        else:
            logger.warning(f"[{instance_id}] Lost the race. Max winners ({max_winners}) already selected.")
            state["instances"][instance_id]["status"] = "loser"
            _write_state(state)
            return False