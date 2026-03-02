import sys
import tkinter as tk
import requests
import file_manager as fm
from gui import MedicalAssistantApp

# --- HACKATHON POLISH: DPI AWARENESS ---
# This makes the Tkinter text and UI elements look sharp on modern screens (Windows).
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass  # Silently ignore if on Mac/Linux

def pre_flight_check():
    """Checks if the local AI server is awake before launching the OS."""
    print("🔍 Pinging local AI engine (Ollama)...")
    try:
        # Ollama's default port
        response = requests.get("http://localhost:11434/", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is ACTIVE and ready.")
    except requests.ConnectionError:
        print("❌ CRITICAL WARNING: Ollama is NOT running!")
        print("   The GUI will open, but all AI features will fail.")
        print("   Fix: Open a terminal and run 'ollama run llama3' before presenting.")
        print("-" * 50)

if __name__ == "__main__":
    print("🏥 Booting AI Medical Diagnostic OS...")

    # 1. Run AI Health Check
    pre_flight_check()

    # 2. Initialize the File System (Creates /case, /.flaggednodes, etc.)
    try:
        fm.init_system()
        print("✅ File system verified: Directories and CSV registries are ready.")
    except Exception as e:
        print(f"❌ Critical Error setting up file system: {e}")
        sys.exit(1)

    # 3. Launch the GUI
    try:
        root = tk.Tk()
        app = MedicalAssistantApp(root)
        print("✅ GUI successfully loaded. Awaiting doctor input...")

        # This keeps the window open and running
        root.mainloop()
    except Exception as e:
        print(f"❌ Application crashed: {e}")