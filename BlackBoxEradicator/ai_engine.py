import requests
import json
import re
import os
import file_manager as fm

OLLAMA_MODEL = "llama3"
URL_GENERATE = "http://localhost:11434/api/generate"
URL_CHAT = "http://localhost:11434/api/chat"

# ==========================================
# ISOLATED MEMORY BANK
# ==========================================
PATIENT_MEMORY = {}


def get_patient_memory(patient_name):
    """Retrieves or initializes an isolated memory string for a specific patient."""
    if patient_name not in PATIENT_MEMORY:
        PATIENT_MEMORY[patient_name] = [
            {"role": "system",
             "content": f"You are a clinical AI diagnostic assistant. You are currently discussing the case of patient: {patient_name}. DO NOT mix details from any other patients. Provide direct, medical answers."}
        ]
    return PATIENT_MEMORY[patient_name]


# ==========================================
# CORE API CALLS
# ==========================================
def query_ollama_generate(prompt, force_json=False):
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    if force_json: payload["format"] = "json"

    try:
        res = requests.post(URL_GENERATE, json=payload, timeout=90)
        res.raise_for_status()
        return res.json().get("response", "")
    except Exception as e:
        print(f"Ollama Error: {e}")
        return ""


def query_ollama_chat(patient_name, new_user_msg):
    memory = get_patient_memory(patient_name)
    memory.append({"role": "user", "content": new_user_msg})

    payload = {
        "model": OLLAMA_MODEL,
        "messages": memory,
        "stream": False
    }

    try:
        res = requests.post(URL_CHAT, json=payload, timeout=60)
        res.raise_for_status()
        ai_response = res.json().get("message", {}).get("content", "")
        memory.append({"role": "assistant", "content": ai_response})
        return ai_response
    except Exception as e:
        memory.pop()
        return f"Error communicating with local AI: {e}"


# ==========================================
# BULLETPROOF JSON PARSER
# ==========================================
def extract_json(text):
    """Indestructible JSON extractor. Ignores all conversational text and markdown."""
    if not text: return {}

    # 1. Strip markdown code blocks if the AI used them
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, flags=re.DOTALL)
    if match:
        text = match.group(1)

    # 2. Find the absolute first and last brackets to isolate the JSON
    text = text.strip()
    start_obj = text.find('{')
    start_arr = text.find('[')

    if start_obj == -1 and start_arr == -1:
        return {}  # Absolutely no JSON found

    # Determine if the AI gave us an object {} or an array [] first
    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        # It's an Object
        end_obj = text.rfind('}')
        if end_obj != -1:
            clean_json = text[start_obj:end_obj + 1]
            try:
                return json.loads(clean_json)
            except:
                pass
    else:
        # It's an Array
        end_arr = text.rfind(']')
        if end_arr != -1:
            clean_json = text[start_arr:end_arr + 1]
            try:
                return json.loads(clean_json)
            except:
                pass

    # Ultimate fallback if the manual isolation fails
    try:
        return json.loads(text)
    except Exception as e:
        print(f"JSON Parsing Error: {e}\nRaw Output was:\n{text}")
        return {}


# ==========================================
# GUI INTEGRATION FUNCTIONS
# ==========================================
def background_extract_for_csv(text):
    prompt = f"""Read this clinical report. Extract the patient's name, summarize symptoms in 3 words, and determine if it is serious (true/false) and recurring (true/false).
    Respond strictly in JSON format: {{"name": "string", "symptoms": "string", "serious": true, "recurring": false}}
    Report: {text}"""

    data = extract_json(query_ollama_generate(prompt, force_json=True))
    if isinstance(data, list) and len(data) > 0: data = data[0]

    name = data.get("name", "Unknown").replace(" ", "_")
    symptoms = data.get("symptoms", "Unknown symptoms")
    is_serious = "Yes" if data.get("serious", False) else "No"
    is_recurring = "Yes" if data.get("recurring", False) else "No"

    return name, symptoms, is_serious, is_recurring


def generate_patient_overview(patient_name):
    history_text = fm.get_patient_history(patient_name)
    if not history_text.strip():
        return "No historical records found for this patient."

    prompt = f"Analyze the following medical records for {patient_name}. Provide a 3-bullet-point clinical overview. Records:\n{history_text}"
    return query_ollama_generate(prompt)


def get_case_historical_connections(patient_name, case_folder):
    history_text = fm.get_patient_history(patient_name)
    case_dir = os.path.join("case", case_folder)
    case_text = ""
    if os.path.exists(case_dir):
        for f in os.listdir(case_dir):
            with open(os.path.join(case_dir, f), 'r') as file:
                case_text += file.read() + "\n"

    prompt = f"""
    Patient: {patient_name}
    Historical Data: {history_text}
    Current Case Data: {case_text}
    Task: Identify any physiological correlations or contradictions. Point out anything the doctor might have missed. Keep it brief.
    """
    return query_ollama_generate(prompt)


def answer_console_question(target_context, msg, node_id):
    if "/" in target_context or "\\" in target_context:
        patient_name = os.path.basename(os.path.dirname(target_context))
    else:
        patient_name = target_context.split("_")[0]

    if not patient_name:
        patient_name = "Unknown_Patient"

    contextual_msg = f"[Context: Doctor is questioning Node {node_id}] Doctor asks: {msg}"
    return query_ollama_chat(patient_name, contextual_msg)


# ==========================================
# DYNAMIC DECISION TREE GENERATOR
# ==========================================
def generate_dynamic_tree(target_text, previous_edits=None):
    """
    Allows the AI to determine the exact length and complexity of the decision tree based on the clinical data.
    """
    edit_context = ""
    if previous_edits:
        edit_context = f"\nTHE DOCTOR MADE THESE CORRECTIONS TO YOUR PREVIOUS LOGIC:\n" + "\n".join(
            previous_edits) + "\nRegenerate the tree and fix your logic based on these corrections."

    prompt = f"""You are a medical AI mapping out a clinical decision tree.
    Text to analyze: {target_text}
    {edit_context}

    Break down the patient's situation into a logical decision tree. 
    YOU decide how many nodes are necessary.

    Output strictly a JSON OBJECT containing an array called "nodes". 
    Use "parent_id" to link them together. The very first node should have a parent_id of null.

    Required JSON structure:
    {{
      "nodes": [
        {{"id": "n1", "parent_id": null, "text": "Assess Vitals: Temp > 100?"}},
        {{"id": "n2", "parent_id": "n1", "text": "Check Lung function: O2 < 92%"}},
        {{"id": "n3", "parent_id": "n2", "text": "Diagnosis: High Risk Pneumonia"}}
      ]
    }}
    Keep the "text" values under 10 words. Output ONLY the JSON.
    """

    raw_response = query_ollama_generate(prompt, force_json=True)

    # Send it through the indestructible parser
    data = extract_json(raw_response)

    # Extract the nodes safely whether the AI wrapped it in a dict or just sent a list
    if isinstance(data, dict) and "nodes" in data:
        nodes = data["nodes"]
    elif isinstance(data, list):
        nodes = data
    else:
        nodes = []

    # Failsafe if the AI completely hallucinated
    if not isinstance(nodes, list) or len(nodes) == 0:
        return [
            {"id": "n1", "parent_id": None, "text": "Error: AI failed to parse JSON."},
            {"id": "n2", "parent_id": "n1", "text": "Check terminal for exactly what it said."}
        ]

    # Clean up to ensure every node has an 'id' before passing to Tkinter
    valid_nodes = [n for n in nodes if isinstance(n, dict) and "id" in n]

    return valid_nodes