import os # For file operations like renaming files and making folders
import json # For reading and writing macro data and hotkeys
import time # Tracks delays between inputs
import threading # To record and execute macros in the background to keep UI responsive
import tkinter as tk # Builds the GUI
from tkinter import simpledialog, messagebox, ttk # For success/error messages, ttk for visuals
from pynput import mouse, keyboard # Import mouse and keyboard parts of pynput
from pynput.mouse import Controller as MouseController, Button # To record mouse inputs and execute inputs in the macros
from pynput.keyboard import Controller as KeyboardController, Key # To record keyboard inputs and execute inputs in the macros
import keyboard as kb # To detect global keypresses and releases and assign hotkeys

# Constants and Globals
MACRO_DIR = "macros" # macro folder
HOTKEY_FILE = "hotkeys.json" # hotkey file
os.makedirs(MACRO_DIR, exist_ok=True) # Make sure MACRO_DIR folder exists

events = []
start_time = None
recording = False
playing = False
record_thread = None

# Recording Functions
def get_time():
    return time.time() - start_time

def on_press(key):
    events.append(('key_press', str(key), get_time()))

def on_release(key):
    events.append(('key_release', str(key), get_time()))
    if str(key) == 'Key.esc':
        return False
    
def on_click(x, y, button, pressed):
    action = 'mouse_press' if pressed else 'mouse_release'
    events.append((action, (x, y, str(button)), get_time()))

def on_move(x, y):
    events.append(('mouse_move', (x, y), get_time()))

def record_macro(macro_name):
    global events, start_time, recording
    events = []
    start_time = time.time()
    recording = True
    with mouse.Listener(on_click=on_click(), on_move=on_move()) as m_listener, keyboard.Listener(on_press=on_press(), on_release=on_release()) as k_listener:
        k_listener.join()
    recording = False
    macro_file = os.path.join(MACRO_DIR, f"{macro_name}.json")
    with open(macro_file, 'w') as f:
        json.dump(events, f)
    messagebox.showinfo("Recording Complete", f"Macro '{macro_name}' saved.")

# Executing Functions
def play_macro(macro_name):
    global playing
    macro_file = os.path.join(MACRO_DIR, f"{macro_name}.json")
    if not os.path.exists(macro_file):
        messagebox.showerror("Error", f"No macro found with name '{macro_name}'")
        return
    
    with open(macro_file, 'r') as f:
        loaded_events = json.load(f)

    mouse_ctl = MouseController()
    keyboard_ctl = KeyboardController()
    playing = True

    for i, event in enumerate(loaded_events):
        if not playing:
            break
        event_type, data, timestamp = event
        time.sleep(timestamp - (loaded_events[i-1][2] if i>0 else 0))

        if event_type == 'mouse_move':
            mouse_ctl.position = tuple(data)
        elif event_type == 'mouse_press':
            x, y, btn = data
            mouse_ctl.position = (x, y)
            mouse_ctl.press(getattr(Button, btn.split('.')[-1]))
        elif event_type == 'mouse_release':
            x, y, btn = data
            mouse_ctl.position = (x, y)
            mouse_ctl.release(getattr(Button, btn.split('.')[-1]))
        elif event_type == 'key_press':
            key = data.strip("'")
            try:
                keyboard_ctl.press(getattr(Key, key.split('.')[-1]))
            except AttributeError:
                keyboard_ctl.press(key)
        elif event_type == 'key_release':
            key = data.strip("'")
            try:
                keyboard_ctl.release(getattr(Key, key.split('.')[-1]))
            except AttributeError:
                keyboard_ctl.release(key)
    playing = False

def stop_playback():
    global playing
    playing = False

# Hotkey Management
def load_hotkeys():
    if not os.path.exists(HOTKEY_FILE):
        return {}
    with open(HOTKEY_FILE, 'r') as f:
        return json.load(f)
    
def save_hotkeys(hotkeys):
    with open(HOTKEY_FILE, 'w') as f:
        json.dump(hotkeys, f)

def assign_hotkey(macro_name, hotkey, save=True):
    hotkeys = load_hotkeys()
    hotkeys[macro_name] = hotkey
    if save:    
        save_hotkeys(hotkeys)
    kb.add_hotkey(hotkey, lambda: threading.Thread(target=play_macro, args=(macro_name,), daemon=True).start())

def bind_all_hotkeys():
    hotkeys = load_hotkeys()
    for macro_name, hotkey in hotkeys.items():
        assign_hotkey(macro_name, hotkey, save=False)

# GUI
def start_recording_gui():
    macro_name = simpledialog.askstring("Macro Name", "Enter a name for the new macro: ")
    if macro_name:
        threading.Thread(target=record_macro, args=(macro_name,), daemon=True).start()
        refresh_macro_list()

def start_playback_gui():
    macro_name = macro_select.get()
    if macro_name:
        threading.Thread(target=play_macro, args=(macro_name,), daemon=True).start()

def assign_hotkey_gui():
    macro_name = macro_select.get()
    if not macro_name:
        return
    hotkey = simpledialog.askstring("Hotkey", f"Assign a hotkey for '{macro_name}' (e.g. ctrl+alt+1): ")
    if hotkey:
        assign_hotkey(macro_name, hotkey)
        messagebox.showinfo("Hotkey Assigned", f"Hotkey '{hotkey}' assigned to '{macro_name}'.")

def rename_macro_gui():
    old_name = macro_select.get()
    if not old_name:
        messagebox.showerror("Error", "No macro selected.")
        return
    new_name = simpledialog.askstring("Rename Macro", f"Enter a new name for {old_name}': ")
    if not new_name:
        return
    
    old_path = os.path.join(MACRO_DIR, f"{old_name}.json")
    new_path = os.path.join(MACRO_DIR, f"{new_name}.json")

    if os.path.exists(new_path):
        messagebox.showerror("Error", f"A macro named '{new_name}' already exists.")
        return
    
    try: 
        os.rename (old_path, new_path)
    except Exception as e:
        messagebox.showerror("Error", f"Could not rename file:\n{e}")
        return
    
    hotkeys = load_hotkeys()
    if old_name in hotkeys:
        hotkeys[new_name] = hotkeys.pop(old_name)
        save_hotkeys(hotkeys)
        kb.remove_all_hotkeys()
        bind_all_hotkeys()

    refresh_macro_list()
    kb.remove_all_hotkeys()
    bind_all_hotkeys()

def rebind_hotkey_gui():
    macro_name = macro_select.get()
    if not macro_name:
        messagebox.showerror("Error", "No macro selected.")
        return
    
    hotkeys = load_hotkeys()
    current_hotkey = hotkeys.get(macro_name, "None")
    prompt = f"Macro '{macro_name}' is currently bound to '{current_hotkey}'. \nEnter a new hotkey (e.g. ctrl+alt+2): "
    new_hotkey = simpledialog.askstring("Rebind Hotkey", prompt)
    if new_hotkey:
        hotkeys[macro_name] - new_hotkey
        save_hotkeys(hotkeys)
        kb.remove_all_hotkeys()
        bind_all_hotkeys()
        messagebox.showinfo("Hotkey Rebound", f"Macro '{macro_name}' is now bound to '{new_hotkey}'.")

def refresh_macro_list():
    macro_files = [f[-5] for f in os.listdir(MACRO_DIR) if f.endswith('.json')]
    macro_select['values'] = macro_files
    if macro_files:
        macro_select.set(macro_files[0])

def build_gui():
    root = tk.Tk()
    root.title("SimpleMacros")
    root.geometry("350x300")

    tk.Label(root, text="Select Macro: ", font=("Arial", 12)).pack(pady=5)

    global macro_select
    macro_select = ttk.Combobox(root, state="readonly", font=("Arial", 10))
    macro_select.pack(pady=5, fill="x", padx=20)

    tk.Button(root, text="Record New Macro", command=start_recording_gui).pack(pady=5)
    tk.Button(root, text="Play Selected Macro", command=start_playback_gui).pack(pady=5)
    tk.Button(root, text="Assign Hotkey", command=assign_hotkey_gui).pack(pady=5)
    tk.Button(root, text="Rebind Hotkey", command=rebind_hotkey_gui).pack(pady=5)
    tk.Button(root, text="Rename Macro", command=rename_macro_gui).pack(pady=5)
    tk.Button(root, text="Stop Playback", command=stop_playback).pack(pady=5)
    
    refresh_macro_list()
    bind_all_hotkeys()
    root.mainloop()

if __name__ == "__main__":
    build_gui()