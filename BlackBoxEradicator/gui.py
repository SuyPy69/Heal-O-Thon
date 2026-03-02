import os
import csv
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Menu
import threading
import datetime
from tkinter import filedialog
import ocr_engine as ocr

import file_manager as fm
import ai_engine as ai
import ml_models as ml

# Ensure all new directories exist
NEW_DIRS = ['case', '.flaggedinfo', '.flaggednodes', 'HistoricalData']
for d in NEW_DIRS:
    os.makedirs(d, exist_ok=True)

PATIENTS_CSV = "patients_overview.csv"
if not os.path.exists(PATIENTS_CSV):
    with open(PATIENTS_CSV, 'w', newline='') as f:
        csv.writer(f).writerow(["Patient_Name", "Symptoms", "Flagged_as_serious", "recurring"])


class MedicalAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🩺 AI Medical Diagnostic OS")
        self.root.geometry("1400x900")
        ttk.Style().theme_use('clam')

        self.selected_node_id = None
        self.tree_edits = []
        self.tree_nodes = []
        self.sidebar_visible = True
        self.current_editing_filepath = None  # Tracks if we are editing an old report

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # The 4 Main Sections
        self.tab_editor = ttk.Frame(self.notebook)
        self.tab_patients = ttk.Frame(self.notebook)
        self.tab_cases = ttk.Frame(self.notebook)
        self.tab_analyze = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_editor, text="📝 Report Editor")
        self.notebook.add(self.tab_patients, text="👥 Patients")
        self.notebook.add(self.tab_cases, text="📁 Current Cases")
        self.notebook.add(self.tab_analyze, text="🧠 Analyze Patient")

        self.setup_editor_tab()
        self.setup_patients_tab()
        self.setup_cases_tab()
        self.setup_analyze_tab()

        # Refresh all data on boot
        self.refresh_all_data()

    # ==========================================
    # TAB 1: REPORT EDITOR & COLLAPSIBLE SIDEBAR
    # ==========================================
    def setup_editor_tab(self):
        # 1. Top Toolbar
        toolbar = ttk.Frame(self.tab_editor)
        toolbar.pack(fill=tk.X, pady=5)

        ttk.Button(toolbar, text=" ≡ ", width=4, command=self.toggle_sidebar).pack(side=tk.LEFT, padx=5)
        ttk.Label(toolbar, text="Write report below. Use '--rerec' to ignore history.",
                  font=("Arial", 10, "italic")).pack(side=tk.LEFT, padx=10)

        self.btn_save = ttk.Button(toolbar, text="💾 Save Report (.med)", command=self.save_report_editor)
        self.btn_save.pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="📸 Scan Physical Report (OCR)", command=self.load_image_report).pack(side=tk.RIGHT,
                                                                                                      padx=5)

        # 2. Paned Window for Sidebar and Editor
        self.editor_paned = ttk.PanedWindow(self.tab_editor, orient=tk.HORIZONTAL)
        self.editor_paned.pack(fill=tk.BOTH, expand=True, pady=5)

        # 3. The Sidebar Frame
        self.sidebar_frame = ttk.Frame(self.editor_paned, width=300)
        self.editor_paned.add(self.sidebar_frame, weight=1)

        sidebar_toolbar = ttk.Frame(self.sidebar_frame)
        sidebar_toolbar.pack(fill=tk.X, pady=2)
        ttk.Label(sidebar_toolbar, text="Patient Reports", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Action Buttons for the Treeview
        ttk.Button(sidebar_toolbar, text="🗑️ Delete", width=10, command=self.delete_selected_reports).pack(
            side=tk.RIGHT, padx=2)
        ttk.Button(sidebar_toolbar, text="➕ Add", width=8, command=self.add_new_report_to_patient).pack(side=tk.RIGHT,
                                                                                                        padx=2)

        # The Treeview (supports Ctrl+Click natively)
        self.report_tree = ttk.Treeview(self.sidebar_frame, selectmode="extended", show="tree")
        self.report_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        tree_scroll = ttk.Scrollbar(self.sidebar_frame, orient="vertical", command=self.report_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_tree.configure(yscrollcommand=tree_scroll.set)

        self.report_tree.bind("<<TreeviewSelect>>", self.on_report_tree_select)

        # 4. The Main Editor Frame
        self.main_editor_frame = ttk.Frame(self.editor_paned)
        self.editor_paned.add(self.main_editor_frame, weight=4)

        self.text_editor = tk.Text(self.main_editor_frame, wrap=tk.WORD, font=("Arial", 11))
        self.text_editor.pack(fill=tk.BOTH, expand=True, padx=5)
        self.clear_editor()

    def toggle_sidebar(self):
        """Hides or shows the patient sidebar."""
        if self.sidebar_visible:
            self.editor_paned.forget(self.sidebar_frame)
            self.sidebar_visible = False
        else:
            self.editor_paned.insert(0, self.sidebar_frame)
            self.sidebar_visible = True

    def refresh_editor_sidebar(self):
        """Populates the Treeview with patients and their reports."""
        self.report_tree.delete(*self.report_tree.get_children())

        if not os.path.exists("HistoricalData"): return

        patients = [d for d in os.listdir("HistoricalData") if os.path.isdir(os.path.join("HistoricalData", d))]
        for patient in sorted(patients):
            # Insert Patient Folder Node
            p_node = self.report_tree.insert('', 'end', text=f"📁 {patient}", values=("patient", patient))

            # Insert Report File Nodes beneath it
            patient_dir = os.path.join("HistoricalData", patient)
            for root_dir, _, files in os.walk(patient_dir):
                for file in sorted(files):
                    if file.endswith(".med"):
                        filepath = os.path.join(root_dir, file)
                        self.report_tree.insert(p_node, 'end', text=f"  📄 {file}", values=("file", filepath))

    def on_report_tree_select(self, event):
        """Loads the selected report into the editor."""
        selected = self.report_tree.selection()
        if len(selected) == 1:
            item = self.report_tree.item(selected[0])
            if item['values'][0] == "file":
                filepath = item['values'][1]
                self.current_editing_filepath = filepath

                # Load text
                with open(filepath, 'r') as f:
                    content = f.read()
                self.text_editor.delete(1.0, tk.END)
                self.text_editor.insert(tk.END, content)

    def add_new_report_to_patient(self):
        """Clears the editor and pre-fills the patient's name."""
        selected = self.report_tree.selection()
        patient_name = ""

        if selected:
            item = self.report_tree.item(selected[0])
            if item['values'][0] == "patient":
                patient_name = item['values'][1]
            elif item['values'][0] == "file":
                # Extract patient name from the file path
                filepath = item['values'][1]
                patient_name = os.path.basename(os.path.dirname(filepath))

        self.clear_editor()
        if patient_name:
            self.text_editor.insert(tk.END, f"Patient Name: {patient_name.replace('_', ' ')}\nSymptoms: \n")

        messagebox.showinfo("New Report",
                            "Editor cleared. You can now write a new report.\nAI will automatically sort it when you save.")

    def delete_selected_reports(self):
        """Handles single and Ctrl-Click multiple deletions with confirmation."""
        selected = self.report_tree.selection()
        if not selected: return

        files_to_delete = []
        for sel in selected:
            item = self.report_tree.item(sel)
            if item['values'][0] == "file":
                files_to_delete.append(item['values'][1])

        if not files_to_delete:
            messagebox.showwarning("Notice", "Please select specific report files (📄) to delete, not patient folders.")
            return

        # Confirmation Dialog
        msg = f"Are you sure you want to permanently delete {len(files_to_delete)} report(s)?"
        if len(files_to_delete) == 1:
            msg = f"Are you sure you want to permanently delete this report?\n{os.path.basename(files_to_delete[0])}"

        if messagebox.askyesno("Confirm Deletion", msg):
            for filepath in files_to_delete:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Failed to delete {filepath}: {e}")

            self.clear_editor()
            self.refresh_all_data()

    def clear_editor(self):
        self.current_editing_filepath = None
        self.text_editor.delete(1.0, tk.END)
        self.text_editor.insert(tk.END, "Patient Name: \nSymptoms: \n")

    def load_image_report(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if not file_path: return

        original_title = self.root.title()
        self.root.title("🩺 AI Medical Diagnostic OS - ⏳ Running OCR Scanner...")
        self.root.update()

        try:
            extracted_text = ocr.extract_text_from_image(file_path)
            self.text_editor.insert(tk.END, f"\n\n--- OCR EXTRACTED TEXT ---\n{extracted_text}\n")
            messagebox.showinfo("OCR Complete",
                                "Text successfully extracted from the scan. You may now review and edit it.")
        except Exception as e:
            messagebox.showerror("OCR Error", f"Failed to run vision engine:\n{e}")
        finally:
            self.root.title(original_title)

    def save_report_editor(self):
        text = self.text_editor.get(1.0, tk.END).strip()
        if not text: return messagebox.showwarning("Empty", "Report is empty.")

        self.original_title = self.root.title()
        self.root.title("🩺 AI Medical Diagnostic OS - ⏳ AI is processing and saving...")
        self.text_editor.config(state="disabled")
        self.btn_save.config(state="disabled")
        self.root.update()

        def background_extraction():
            try:
                name, symptoms, is_serious, is_recurring = ai.background_extract_for_csv(text)
                self.root.after(0, lambda: self.finish_saving_report(name, symptoms, is_serious, is_recurring, text))
            except Exception as e:
                self.root.after(0, lambda: self._reset_editor_ui(f"AI Extraction Failed: {e}"))

        threading.Thread(target=background_extraction, daemon=True).start()

    def finish_saving_report(self, name, symptoms, is_serious, is_recurring, text):
        if name == "Unknown":
            name = simpledialog.askstring("Patient Name", "AI couldn't find a name. Enter Patient Name:")
            if not name:
                self._reset_editor_ui()
                return

        # Let AI do the sorting - if we are editing an old file, and the AI detected the same name, overwrite it.
        # Otherwise, save as a new file.
        if self.current_editing_filepath and name in self.current_editing_filepath:
            filepath = self.current_editing_filepath
        else:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"{name}_{date_str}.med"
            patient_dir = os.path.join("HistoricalData", name)
            os.makedirs(patient_dir, exist_ok=True)
            filepath = os.path.join(patient_dir, filename)

        with open(filepath, 'w') as f:
            f.write(text)

        # Append to CSV
        with open(PATIENTS_CSV, 'a', newline='') as f:
            csv.writer(f).writerow([name, symptoms, is_serious, is_recurring])

        self._reset_editor_ui()
        messagebox.showinfo("Saved", f"Report saved to:\n{filepath}")
        self.refresh_all_data()

    def _reset_editor_ui(self, error_msg=None):
        self.text_editor.config(state="normal")
        self.btn_save.config(state="normal")
        self.root.title(self.original_title)
        if error_msg: messagebox.showerror("Error", error_msg)

    # ==========================================
    # TAB 2: PATIENTS SECTION
    # ==========================================
    def setup_patients_tab(self):
        paned = ttk.PanedWindow(self.tab_patients, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)

        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        ttk.Label(left_frame, text="Patient List", font=("Arial", 12, "bold")).pack(pady=5)

        self.patient_listbox = tk.Listbox(left_frame, font=("Arial", 11))
        self.patient_listbox.pack(fill=tk.BOTH, expand=True)
        self.patient_listbox.bind("<<ListboxSelect>>", self.on_patient_select)

        self.right_frame = ttk.Frame(paned)
        paned.add(self.right_frame, weight=3)

        self.overview_text = tk.Text(self.right_frame, wrap=tk.WORD, font=("Arial", 11), state="disabled", height=15)
        self.overview_text.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_frame = ttk.Frame(self.right_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🌳 Run Diagnostic Tree",
                   command=lambda: self.notebook.select(self.tab_analyze)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💬 Run Discussion", command=self.run_discussion).pack(side=tk.LEFT, padx=5)

    def on_patient_select(self, event):
        sel = self.patient_listbox.curselection()
        if not sel: return
        patient = self.patient_listbox.get(sel[0])

        self.overview_text.config(state="normal")
        self.overview_text.delete(1.0, tk.END)
        self.overview_text.insert(tk.END, f"⏳ AI is scanning records for {patient}. Please wait...\n\n")
        self.overview_text.config(state="disabled")
        self.root.update()

        def fetch_overview():
            overview = ai.generate_patient_overview(patient)
            self.root.after(0, lambda: self._update_overview_ui(overview))

        threading.Thread(target=fetch_overview, daemon=True).start()

    def _update_overview_ui(self, result_text):
        self.overview_text.config(state="normal")
        self.overview_text.insert(tk.END, result_text)
        self.overview_text.config(state="disabled")

    def run_discussion(self):
        messagebox.showinfo("Discussion", "AI Discussion module initiated for selected patient.")

    # ==========================================
    # TAB 3: CURRENT CASES
    # ==========================================
    def setup_cases_tab(self):
        toolbar = ttk.Frame(self.tab_cases)
        toolbar.pack(fill=tk.X, pady=5)
        ttk.Button(toolbar, text="(+) Create New Case", command=self.create_case).pack(side=tk.LEFT, padx=5)

        paned = ttk.PanedWindow(self.tab_cases, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)

        self.case_listbox = tk.Listbox(paned, font=("Arial", 11))
        paned.add(self.case_listbox, weight=1)
        self.case_listbox.bind("<<ListboxSelect>>", self.on_case_select)

        self.case_insights_text = tk.Text(paned, wrap=tk.WORD, font=("Arial", 11), state="disabled")
        paned.add(self.case_insights_text, weight=3)

    def create_case(self):
        patient = simpledialog.askstring("New Case", "Enter Patient Name:")
        if not patient: return
        casename = simpledialog.askstring("New Case", "Enter Case Name (e.g., Chronic_Cough):")
        if not casename: return

        folder_name = f"{patient}_{casename}"
        os.makedirs(os.path.join("case", folder_name), exist_ok=True)
        self.refresh_all_data()
        messagebox.showinfo("Success", f"Case folder created: /case/{folder_name}")

    def on_case_select(self, event):
        sel = self.case_listbox.curselection()
        if not sel: return
        case_folder = self.case_listbox.get(sel[0])
        patient_name = case_folder.split("_")[0]

        self.case_insights_text.config(state="normal")
        self.case_insights_text.delete(1.0, tk.END)
        self.case_insights_text.insert(tk.END, f"--- AI INSIGHTS FOR CASE: {case_folder} ---\n")
        self.case_insights_text.insert(tk.END, f"⏳ Linking case to historical data for {patient_name}...\n\n")
        self.case_insights_text.config(state="disabled")
        self.root.update()

        def fetch_case_insights():
            insights = ai.get_case_historical_connections(patient_name, case_folder)
            self.root.after(0, lambda: self._update_case_ui(insights))

        threading.Thread(target=fetch_case_insights, daemon=True).start()

    def _update_case_ui(self, result_text):
        self.case_insights_text.config(state="normal")
        self.case_insights_text.insert(tk.END, result_text)
        self.case_insights_text.config(state="disabled")

    # ==========================================
    # TAB 4: ANALYZE PATIENT (DYNAMIC Tree & Console)
    # ==========================================
    def setup_analyze_tab(self):
        top_frame = ttk.Frame(self.tab_analyze)
        top_frame.pack(fill=tk.X, pady=5)

        self.analysis_mode = tk.StringVar(value="singular")
        ttk.Radiobutton(top_frame, text="Singular Report", variable=self.analysis_mode, value="singular",
                        command=self.toggle_analysis_mode).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_frame, text="Multiple Reports / Case", variable=self.analysis_mode, value="multiple",
                        command=self.toggle_analysis_mode).pack(side=tk.LEFT, padx=5)

        self.target_combo = ttk.Combobox(top_frame, state="readonly", width=40)
        self.target_combo.pack(side=tk.LEFT, padx=10)

        ttk.Button(top_frame, text="▶ Generate Decision Tree", command=self.generate_tree, style="Accent.TButton").pack(
            side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🧹 Clear Edits", command=self.clear_edits).pack(side=tk.LEFT, padx=5)

        work_paned = ttk.PanedWindow(self.tab_analyze, orient=tk.VERTICAL)
        work_paned.pack(fill=tk.BOTH, expand=True, pady=5)

        self.canvas = tk.Canvas(work_paned, bg="#f8f9fa")
        work_paned.add(self.canvas, weight=4)

        self.node_menu = Menu(self.root, tearoff=0)
        self.node_menu.add_command(label="✅ Tick (Confirm)", command=lambda: self.mark_node("tick"))
        self.node_menu.add_command(label="🚩 Flag (Mark False)", command=lambda: self.mark_node("flag"))
        self.node_menu.add_separator()
        self.node_menu.add_command(label="❓ Question this Node", command=self.question_node)

        self.canvas.bind("<Button-1>", self.on_canvas_left_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

        console_frame = ttk.Frame(work_paned)
        work_paned.add(console_frame, weight=1)

        self.console_log = tk.Text(console_frame, height=5, state="disabled", font=("Consolas", 10), bg="#2d3436",
                                   fg="#dfe6e9")
        self.console_log.pack(fill=tk.BOTH, expand=True)

        entry_frame = ttk.Frame(console_frame)
        entry_frame.pack(fill=tk.X)
        ttk.Label(entry_frame, text="Ask AI about selected node:").pack(side=tk.LEFT, padx=5)
        self.console_entry = ttk.Entry(entry_frame)
        self.console_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.console_entry.bind("<Return>", self.send_to_console)

    def toggle_analysis_mode(self):
        mode = self.analysis_mode.get()
        if mode == "singular":
            files = []
            for root, _, fs in os.walk("HistoricalData"):
                for f in fs:
                    if f.endswith(".med"): files.append(os.path.join(root, f))
            self.target_combo['values'] = files
        else:
            cases = os.listdir("case")
            self.target_combo['values'] = cases

    def clear_edits(self):
        self.tree_edits = []
        messagebox.showinfo("Cleared", "Doctor's manual corrections have been cleared.")
        self.generate_tree()

    def generate_tree(self):
        target = self.target_combo.get()
        if not target: return messagebox.showwarning("Select", "Select a target first.")

        self.canvas.delete("all")
        self.log_to_console(f"System: AI is analyzing {target} and generating the tree...")
        self.canvas.create_text(600, 150, text="⏳ AI IS RETHINKING DECISION TREE...", font=("Arial", 16, "bold"),
                                fill="blue", tags="loading")
        self.root.update()

        # Extract target text
        if self.analysis_mode.get() == "singular":
            try:
                with open(target, 'r') as f:
                    target_text = f.read()
            except Exception as e:
                target_text = f"Error: {e}"
        else:
            target_text = fm.get_case_history(target)

        def fetch_tree():
            self.tree_nodes = ai.generate_dynamic_tree(target_text, self.tree_edits)
            self.root.after(0, self.draw_fetched_tree)

        threading.Thread(target=fetch_tree, daemon=True).start()

    def draw_fetched_tree(self):
        self.canvas.delete("loading")

        if not self.tree_nodes or not isinstance(self.tree_nodes, list):
            self.canvas.create_text(600, 150, text="Failed to generate tree layout.", fill="red", font=("Arial", 14))
            return

        # --- AUTO-LAYOUT ALGORITHM ---
        children_map = {n["id"]: [] for n in self.tree_nodes}
        root_nodes = []

        for node in self.tree_nodes:
            pid = node.get("parent_id")
            if pid and pid in children_map:
                children_map[pid].append(node["id"])
            else:
                root_nodes.append(node["id"])

        if not root_nodes and self.tree_nodes:
            root_nodes.append(self.tree_nodes[0]["id"])

        depths = {}

        def assign_depth(node_id, d):
            depths[node_id] = d
            for child_id in children_map.get(node_id, []):
                assign_depth(child_id, d + 1)

        for r in root_nodes: assign_depth(r, 0)

        level_nodes = {}
        for node in self.tree_nodes:
            d = depths.get(node["id"], 0)
            if d not in level_nodes: level_nodes[d] = []
            level_nodes[d].append(node)

        canvas_width = 1200
        y_start = 80
        y_step = 130

        node_coords = {}
        for d, nodes_in_level in level_nodes.items():
            num_nodes = len(nodes_in_level)
            spacing = canvas_width / (num_nodes + 1)
            y = y_start + (d * y_step)
            for i, node in enumerate(nodes_in_level):
                x = spacing * (i + 1)
                node_coords[node["id"]] = (x, y)
                node["x"] = x
                node["y"] = y

        for node in self.tree_nodes:
            pid = node.get("parent_id")
            if pid and pid in node_coords:
                px, py = node_coords[pid]
                cx, cy = node_coords[node["id"]]
                self.canvas.create_line(px, py + 35, cx, cy - 35, arrow=tk.LAST, width=2)

        for node in self.tree_nodes:
            x, y = node["x"], node["y"]
            text = node.get("text", "Unknown")
            if len(text) > 30: text = text[:30] + "\n" + text[30:]

            self.canvas.create_rectangle(x - 120, y - 35, x + 120, y + 35, fill="#ffeaa7", outline="black", width=2,
                                         tags=("node", node["id"]))
            self.canvas.create_text(x, y, text=text, justify="center", width=220, font=("Arial", 10, "bold"),
                                    tags=("node", node["id"]))

    def on_canvas_left_click(self, event):
        item = self.canvas.find_withtag("current")
        if not item: return
        tags = self.canvas.gettags(item[0])
        for tag in tags:
            if tag.startswith("n"):
                self.selected_node_id = tag
                node_text = next((n.get("text", "") for n in self.tree_nodes if n["id"] == tag), "")

                new_text = simpledialog.askstring("Edit Node", "Edit AI's assumption:", initialvalue=node_text)
                if new_text and new_text != node_text:
                    self.log_to_console(f"Doctor corrected node {tag}. AI rethinking sub-nodes...")
                    self.tree_edits.append(f"Regarding '{node_text}', the doctor corrected it to: '{new_text}'")
                    self.generate_tree()
                break

    def on_canvas_right_click(self, event):
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            for tag in tags:
                if tag.startswith("n"):
                    self.selected_node_id = tag
                    self.node_menu.post(event.x_root, event.y_root)
                    break

    def mark_node(self, action):
        if not self.selected_node_id: return
        node = next((n for n in self.tree_nodes if n["id"] == self.selected_node_id), None)
        if not node: return

        if action == "flag":
            filepath = os.path.join(".flaggednodes", f"{self.selected_node_id}_flag.txt")
            with open(filepath, 'w') as f:
                f.write(node.get("text", ""))
            self.log_to_console(f"System: Node {self.selected_node_id} FLAGGED. Saved to .flaggednodes.")
            self.canvas.itemconfig(self.selected_node_id, fill="#ff7675")
        else:
            self.log_to_console(f"System: Node {self.selected_node_id} TICKED (Confirmed).")
            self.canvas.itemconfig(self.selected_node_id, fill="#55efc4")

    def question_node(self):
        if not self.selected_node_id: return
        self.console_entry.delete(0, tk.END)
        self.console_entry.insert(0, f"Regarding Node {self.selected_node_id}: Why did you assume this?")
        self.console_entry.focus()

    def send_to_console(self, event):
        msg = self.console_entry.get()
        if not msg: return
        self.console_entry.delete(0, tk.END)
        self.log_to_console(f"Doctor: {msg}")

        target = self.target_combo.get()
        self.console_entry.config(state="disabled")
        self.log_to_console("AI: Thinking...")

        def fetch_response():
            response = ai.answer_console_question(target, msg, self.selected_node_id)
            self.root.after(0, lambda: self._update_console_ui(response))

        threading.Thread(target=fetch_response, daemon=True).start()

    def _update_console_ui(self, response):
        self.console_log.config(state="normal")
        text_content = self.console_log.get("1.0", "end-1c")
        lines = text_content.split('\n')
        self.console_log.delete("1.0", tk.END)
        self.console_log.insert(tk.END, '\n'.join(lines[:-2]) + "\n")

        self.log_to_console(f"AI: {response}")
        self.console_entry.config(state="normal")
        self.console_entry.focus()

    def log_to_console(self, text):
        self.console_log.config(state="normal")
        self.console_log.insert(tk.END, text + "\n")
        self.console_log.see(tk.END)
        self.console_log.config(state="disabled")

    # ==========================================
    # UTILS
    # ==========================================
    def refresh_all_data(self):
        self.refresh_editor_sidebar()

        self.patient_listbox.delete(0, tk.END)
        if os.path.exists("HistoricalData"):
            for p in os.listdir("HistoricalData"):
                if os.path.isdir(os.path.join("HistoricalData", p)):
                    self.patient_listbox.insert(tk.END, p)

        self.case_listbox.delete(0, tk.END)
        if os.path.exists("case"):
            for c in os.listdir("case"):
                self.case_listbox.insert(tk.END, c)

        self.toggle_analysis_mode()


if __name__ == "__main__":
    pass