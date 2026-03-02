import numpy as np
from sklearn.tree import DecisionTreeClassifier


def train_and_get_models():
    """
    Instead of 5 hardcoded arrays, we generate a synthetic dataset of 200 patients.
    This forces the Decision Tree to actually learn complex, multi-level clinical rules
    (e.g., checking O2, then checking Temp if O2 is borderline) so your GUI looks impressive.
    """
    print("⚙️ Booting ML Engine: Generating synthetic clinical training data...")

    np.random.seed(42)  # Keeps the generated data consistent every time you run the app

    # 1. Generate 100 "Healthy/Low Risk" patients
    # Normal Temp (97-99), Normal HR (60-90), Normal O2 (95-100)
    healthy_temp = np.random.uniform(97.0, 99.5, 100)
    healthy_hr = np.random.uniform(60, 90, 100)
    healthy_o2 = np.random.uniform(95, 100, 100)
    healthy_X = np.column_stack((healthy_temp, healthy_hr, healthy_o2))
    healthy_y = np.zeros(100)  # 0 = Low Risk

    # 2. Generate 100 "Sick/High Risk" patients
    # High Temp (100-104), High HR (90-130), Low O2 (85-94)
    sick_temp = np.random.uniform(100.0, 104.0, 100)
    sick_hr = np.random.uniform(90, 130, 100)
    sick_o2 = np.random.uniform(85, 94, 100)
    sick_X = np.column_stack((sick_temp, sick_hr, sick_o2))
    sick_y = np.ones(100)  # 1 = High Risk

    # Combine them into our final training set
    X_train = np.vstack((healthy_X, sick_X))
    y_train = np.concatenate((healthy_y, sick_y))

    # 3. Train the Model
    # max_depth=3 ensures the tree doesn't grow so massive that it goes off the edges of your Tkinter Canvas.
    tree_model = DecisionTreeClassifier(max_depth=3, random_state=42)
    tree_model.fit(X_train, y_train)

    return tree_model


def get_tree_path_steps(tree_model, temp, hr, o2_sat):
    """
    Scikit-Learn trees are built using parallel C-arrays under the hood.
    This function translates that mathematical structure into a simple list of English steps
    so the Tkinter GUI knows exactly what boxes and lines to draw on the canvas.
    """
    feature_names = ['Temperature', 'Heart_Rate', 'O2_Sat']

    # Format the patient's data into the 2D array format sklearn expects
    input_vec = np.array([[temp, hr, o2_sat]])

    # 'decision_path' returns a sparse matrix showing exactly which nodes this specific patient passed through.
    node_indicator = tree_model.decision_path(input_vec)

    # 'apply' tells us the ID of the final "Leaf" (the end result node) the patient landed on.
    leaf_id = tree_model.apply(input_vec)[0]

    # These are the parallel arrays that hold the actual rules of the tree.
    # feature[node_id] tells us WHICH feature is being checked (0=Temp, 1=HR, 2=O2)
    feature_array = tree_model.tree_.feature
    # threshold[node_id] tells us the NUMBER it is splitting at (e.g., Temp <= 99.5)
    threshold_array = tree_model.tree_.threshold

    # Convert the sparse matrix into a simple list of node IDs this patient visited.
    node_index = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]

    steps = []

    # Iterate through every node the patient visited to build the story.
    for node_id in node_index:

        # SCENARIO A: We reached the end of the tree (The Result Leaf)
        if leaf_id == node_id:
            # Predict whether they are 0 (Low Risk) or 1 (High Risk)
            pred = tree_model.predict(input_vec)[0]
            diag = "High Risk (Admit to Ward)" if pred == 1 else "Low Risk (Outpatient Care)"

            steps.append({
                "type": "leaf",
                "text": f"FINAL DIAGNOSIS:\n{diag}",
                "pred": pred
            })
            break  # Stop traversing, we hit the end.

        # SCENARIO B: We are at a routing node (A question/decision block)
        # 1. Figure out which feature is being checked at this specific node
        feature_idx = feature_array[node_id]
        feature_name = feature_names[feature_idx]

        # 2. Figure out the cutoff limit the AI learned for this node
        thresh_val = threshold_array[node_id]

        # 3. Look at what the patient's ACTUAL value is
        actual_val = input_vec[0, feature_idx]

        # 4. Determine which way the patient went (True/False branch)
        if actual_val <= thresh_val:
            path_taken = f"<= {thresh_val:.1f} (Went Left)"
        else:
            path_taken = f"> {thresh_val:.1f} (Went Right)"

        # 5. Format it cleanly for the GUI Canvas to display in the yellow box
        display_text = f"Node {node_id}: Check {feature_name}\nPatient: {actual_val}\nRule: {path_taken}"

        steps.append({
            "type": "node",
            "feature": feature_name,  # Used by the GUI to know what to ask if the doctor flags it
            "threshold": thresh_val,
            "actual": actual_val,  # The patient's actual number
            "text": display_text  # The text drawn inside the canvas rectangle
        })

    return steps