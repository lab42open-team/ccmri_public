#!/usr/bin/python3.5
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score, confusion_matrix)
import os
import sys
import pickle

# Parameters
# terrestrial training dataset
#Note: please edit accordignly to make the following file paths functional
file_paths = [
    '/_full_path_in_your_server_to_/k_folds_combined_super_vector.csv',
]
# aquatic training dataset
#file_paths = [
#    '/_full_path_in_your_server_to_/k_folds_aquatic_training_super_vector.csv',
#]
# combined training dataset
#file_paths = [
#    '/_full_path_in_your_server_to_/all_training_combined_super_vector.csv',
#]



model_choice = ['logistic_regression']
model_folder = '/_full_path_in_your_server_to_/models'
threshold_range = [0.5]
#multiple thresholds
#num_steps = 3  # for example, creates [0.0, 0.25, 0.5, 0.75, 1.0]
#threshold_range = np.linspace(0, 1, num=num_steps).tolist()

output_dir = '/_full_path_in_your_server_to_/output'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

models_dir = os.path.join(output_dir, 'models')
if not os.path.exists(models_dir):
    os.makedirs(models_dir)

# Check for correct number of arguments
if len(sys.argv) != 3:
    print("Usage: python script_name.py <k> <n_repeats>")
    sys.exit(1)

try:
    k = int(sys.argv[1])
    n_repeats = int(sys.argv[2])
except ValueError:
    print("Both k and n_repeats must be integers.")
    sys.exit(1)

print("Number of folds (k):", k)
print("Number of repeats (n_repeats):", n_repeats)

output_file = os.path.join(output_dir, 'training_metrics_table_with_thresholds.tsv')

# Write headers if the file is new or empty
try:
    with open(output_file, 'r') as f:
        if f.readline().strip() == "":
            with open(output_file, 'w') as f_write:
                f_write.write(
                    "model\tdataset\tk\tn_repeats\tthreshold\taccuracy\tprecision\trecall\tspecificity\tf1\ttp\ttn\tfp\tfn\n"
                )
except FileNotFoundError:
    with open(output_file, 'w') as f_write:
        f_write.write(
            "model\tdataset\tk\tn_repeats\tthreshold\taccuracy\tprecision\trecall\tspecificity\tf1\ttp\ttn\tfp\tfn\n"
        )

# K-Fold training + evaluation
for dataset in file_paths:
    for m_choice in model_choice:
        data = pd.read_csv(dataset)
        X = data.drop(columns=['cc', 'Study'])
        y = data['cc']

        if m_choice == 'logistic_regression':
            model = LogisticRegression(max_iter=1000)
        else:
            print("Invalid model choice.")
            continue

        results = []

        for repeat in range(1, n_repeats + 1):
            print("Starting Repeat {} of {}".format(repeat, n_repeats))
            kf = KFold(n_splits=k, shuffle=True, random_state=None)
            for fold, (train_idx, test_idx) in enumerate(kf.split(X), start=1):
                print("Processing Fold {} of {} for {} with dataset '{}' (Repeat {})".format(
                    fold, k, m_choice, dataset.split('/')[-1].replace('.csv', ''), repeat))

                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

                model.fit(X_train, y_train)

                print("Model coefficients for repeat {}, fold {}:".format(repeat, fold))
                print(model.coef_)
                print("Intercept: ", model.intercept_)

                # Save the model
                model_name_file = "{}_repeat{}_fold{}_{}.pkl".format(
                    m_choice,
                    repeat,
                    fold,
                    dataset.split('/')[-1].replace('.csv', '')
                )
                model_path = os.path.join(models_dir, model_name_file)
                with open(model_path, 'wb') as f_model:
                    pickle.dump({'model': model, 'columns': list(X.columns)}, f_model)

                print("Model saved:", model_path)

                y_proba = model.predict_proba(X_test)[:, 1]
                for threshold in threshold_range:
                    y_pred = (y_proba >= threshold).astype(int)

                    accuracy = accuracy_score(y_test, y_pred)
                    precision = precision_score(y_test, y_pred, zero_division=0)
                    recall = recall_score(y_test, y_pred, zero_division=0)
                    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
                    specificity = float(tn) / (tn + fp) if (tn + fp) > 0 else 0
                    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0

                    results.append({
                        "model": m_choice,
                        "dataset": dataset.split('/')[-1].replace('.csv', ''),
                        "k": k,
                        "n_repeats": n_repeats,
                        "threshold": threshold,
                        "accuracy": accuracy,
                        "precision": precision,
                        "recall": recall,
                        "specificity": specificity,
                        "f1": f1,
                        "tp": tp,
                        "tn": tn,
                        "fp": fp,
                        "fn": fn
                    })

        results_df = pd.DataFrame(results)

        avg_results = results_df.groupby(['model', 'dataset', 'k', 'threshold']).agg({
            'accuracy': 'mean',
            'precision': 'mean',
            'recall': 'mean',
            'specificity': 'mean',
            'f1': 'mean',
            'tp': 'mean',
            'tn': 'mean',
            'fp': 'mean',
            'fn': 'mean'
        }).reset_index()

        with open(output_file, 'a') as f:
            for _, result in results_df.iterrows():
                f.write(
                    "{}\t{}\t{}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\n".format(
                        result["model"],
                        result["dataset"],
                        result["k"],
                        n_repeats,
                        result["threshold"],
                        result["accuracy"],
                        result["precision"],
                        result["recall"],
                        result["specificity"],
                        result["f1"],
                        result["tp"],
                        result["tn"],
                        result["fp"],
                        result["fn"]
                    )
                )

            for _, result in avg_results.iterrows():
                f.write(
                    "{}\tavg_{}\t{}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\n".format(
                        result["model"],
                        result["dataset"],
                        result["k"],
                        n_repeats,
                        result["threshold"],
                        result["accuracy"],
                        result["precision"],
                        result["recall"],
                        result["specificity"],
                        result["f1"],
                        result["tp"],
                        result["tn"],
                        result["fp"],
                        result["fn"]
                    )
                )
