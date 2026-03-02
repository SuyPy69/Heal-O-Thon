import os
import csv
import datetime
import difflib

# The new expanded directory structure for the Medical OS
DIRS = ['HistoricalData', 'case', '.flaggedinfo', '.flaggednodes']
PATIENTS_CSV = "patients_overview.csv"


def init_system():
    """Initializes all required folders and the main patient CSV registry."""
    for d in DIRS:
        os.makedirs(d, exist_ok=True)

    if not os.path.exists(PATIENTS_CSV):
        with open(PATIENTS_CSV, 'w', newline='') as f:
            csv.writer(f).writerow(["Patient_Name", "Symptoms", "Flagged_as_serious", "recurring"])


# ==========================================
# PATIENT REGISTRY & TYPO CHECKING
# ==========================================
def get_patients():
    """Returns a list of all patient folder names from HistoricalData."""
    if not os.path.exists("HistoricalData"): return []
    return [d for d in os.listdir("HistoricalData") if os.path.isdir(os.path.join("HistoricalData", d))]


def check_for_typos(extracted_name):
    """Checks if the extracted name is a slight typo of an existing patient."""
    existing_patients = get_patients()
    if not existing_patients or extracted_name in existing_patients:
        return None  # No typo or exact match

    # Find close matches (e.g., "Jon Doe" -> "John_Doe")
    matches = difflib.get_close_matches(extracted_name, existing_patients, n=1, cutoff=0.7)
    if matches:
        return matches[0]  # Returns the suggested correct name
    return None


def update_patient_csv(name, symptoms, is_serious, is_recurring):
    """Appends newly analyzed patient reports to the overview CSV."""
    with open(PATIENTS_CSV, 'a', newline='') as f:
        csv.writer(f).writerow([name, symptoms, is_serious, is_recurring])


# ==========================================
# .MED FILE SAVING & HISTORY AGGREGATION
# ==========================================
def save_med_report(name, text, subfolder=None):
    """Saves report as PatientName_Date_Time(Hour-Mins).med"""
    base_dir = os.path.join("HistoricalData", name)
    if subfolder:
        base_dir = os.path.join(base_dir, subfolder)

    os.makedirs(base_dir, exist_ok=True)

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")  # Using dash instead of colon for Windows file safety

    filename = f"{name}_{date_str}_{time_str}.med"
    filepath = os.path.join(base_dir, filename)

    with open(filepath, 'w') as f:
        f.write(text)
    return filepath


def get_patient_history(name):
    """Reads all .med files for a patient. Returns combined text."""
    base_dir = os.path.join("HistoricalData", name)
    if not os.path.exists(base_dir): return ""

    history_text = ""
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".med"):
                with open(os.path.join(root, file), 'r') as f:
                    history_text += f"\n--- File: {file} ---\n{f.read()}\n"
    return history_text


# ==========================================
# CASE MANAGEMENT
# ==========================================
def create_case_folder(patient_name, case_name):
    """Creates a specific case folder for tracking a targeted illness."""
    folder_name = f"{patient_name}_{case_name}"
    path = os.path.join("case", folder_name)
    os.makedirs(path, exist_ok=True)
    return path


def get_cases():
    """Returns a list of all active cases."""
    if not os.path.exists("case"): return []
    return [d for d in os.listdir("case") if os.path.isdir(os.path.join("case", d))]


def get_case_history(case_folder_name):
    """Reads all documents associated with a specific case."""
    case_dir = os.path.join("case", case_folder_name)
    if not os.path.exists(case_dir): return ""

    case_text = ""
    for file in os.listdir(case_dir):
        with open(os.path.join(case_dir, file), 'r') as f:
            case_text += f"\n--- Case File: {file} ---\n{f.read()}\n"
    return case_text


# ==========================================
# FLAGGING ENGINE (Nodes & Info)
# ==========================================
def save_flagged_node(node_id, text):
    """Saves a decision tree node that the doctor marked as incorrect."""
    filepath = os.path.join(".flaggednodes", f"{node_id}_flag.txt")
    with open(filepath, 'w') as f:
        f.write(text)
    return filepath


def save_flagged_info(info_id, text):
    """Saves general case information that the doctor flagged as irrelevant/wrong."""
    filepath = os.path.join(".flaggedinfo", f"{info_id}_flag.txt")
    with open(filepath, 'w') as f:
        f.write(text)
    return filepath