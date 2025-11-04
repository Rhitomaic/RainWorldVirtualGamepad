#!/usr/bin/env python3
import uinput
from evdev import InputDevice, ecodes
import threading
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# --- Configuration ---
KEYBOARD_PATH = "/dev/input/event2"
# Replace with your keyboard device path, for me, it's event2, you can run `sudo evtest` after installing `evtest`
# and see where your keyboard is.

# --- Virtual Gamepad Setup ---
gamepad_events = (
    uinput.BTN_A,
    uinput.BTN_B,
    uinput.BTN_X,
    uinput.BTN_Y,
    uinput.BTN_TL,
    uinput.BTN_TR,
    uinput.BTN_START,
    uinput.BTN_SELECT,
    uinput.ABS_X + (-1, 1, 0, 0),
    uinput.ABS_Y + (-1, 1, 0, 0),
)

device = uinput.Device(gamepad_events, name="Virtual Gamepad")
keyboard = InputDevice(KEYBOARD_PATH)

logging.info(f"Using keyboard device: {keyboard.name} ({KEYBOARD_PATH})")
logging.info("Listening for keyboard input... (Ctrl+C to stop)")

# --- Key Mappings ---
key_map = {
    ecodes.KEY_Z: uinput.BTN_A,        # Z -> A (Jump)
    ecodes.KEY_C: uinput.BTN_B,        # C -> B (Throw)
    ecodes.KEY_X: uinput.BTN_X,        # X -> X (Pick Up/Eat)
    ecodes.KEY_V: uinput.BTN_Y,        # V -> Y (Special)
    ecodes.KEY_A: uinput.BTN_TR,       # A -> Right Shoulder (Map)
    ecodes.KEY_ESC: uinput.BTN_SELECT, # ESC -> Back/Menu (Pause/Exit)
}

# --- D-pad actions or something ---
dpad_state = {
    'ABS_X': 0,
    'ABS_Y': 0
}
pressed_dirs = {
    'left': False,
    'right': False,
    'up': False,
    'down': False,
}

running = True
def handle_exit(signum, frame):
    global running
    running = False
    logging.info("Stopping listener...")

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

"""
Recalculate and emit axis value based on which directions are held.
Otherwise, the input might be funky, cuz like, yeah.
"""
def update_axis_state(axis):
    if axis == 'ABS_X':
        if pressed_dirs['left'] and not pressed_dirs['right']:
            value = -1
        elif pressed_dirs['right'] and not pressed_dirs['left']:
            value = 1
        else:
            value = 0
    else:  # ABS_Y
        if pressed_dirs['up'] and not pressed_dirs['down']:
            value = -1
        elif pressed_dirs['down'] and not pressed_dirs['up']:
            value = 1
        else:
            value = 0

    dpad_state[axis] = value
    device.emit(getattr(uinput, axis), value)
    logging.info(f"{axis} updated -> {value}")

def handle_key_event(event):
    # Ignore repeats
    if event.value not in (0, 1):
        return

    code = event.code
    value = event.value

    if code in key_map:
        device.emit(key_map[code], value)
        state = "pressed" if value else "released"
        logging.info(f"Key {ecodes.KEY[code]} {state} -> Gamepad {key_map[code]}")
        return

    # Handle D-pad logic with directional state
    if code == ecodes.KEY_LEFT:
        pressed_dirs['left'] = bool(value)
        update_axis_state('ABS_X')

    elif code == ecodes.KEY_RIGHT:
        pressed_dirs['right'] = bool(value)
        update_axis_state('ABS_X')

    elif code == ecodes.KEY_UP:
        pressed_dirs['up'] = bool(value)
        update_axis_state('ABS_Y')

    elif code == ecodes.KEY_DOWN:
        pressed_dirs['down'] = bool(value)
        update_axis_state('ABS_Y')

def keyboard_listener():
    for event in keyboard.read_loop():
        if not running:
            break
        if event.type == ecodes.EV_KEY:
            handle_key_event(event)

listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
listener_thread.start()

try:
    while running:
        pass
except KeyboardInterrupt:
    pass
finally:
    device.destroy()
    logging.info("Virtual gamepad stopped cleanly.")
    sys.exit(0)
