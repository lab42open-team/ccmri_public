#!/usr/bin/python3.5
import pandas as pd
import numpy as np
import os
import pickle
import re
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix
import statistics

def align_columns(X_val_full, trained_columns, log_file="/_full_path_in_your_server_to_/your_log.txt"):
    with open(log_file, 'w') as log:
        if not isinstance(X_val_full, pd.DataFrame):
            log.write("ERROR: X_val_full is not a pandas DataFrame. Type: {}\n".format(type(X_val_full)))
            raise TypeError("X_val_full is not a pandas DataFrame. Type: {}".format(type(X_val_full)))

        log.write("Validation DataFrame successfully confirmed.\n")
        X_val_full.columns = X_val_full.columns.str.strip()
        trained_columns = [col.strip() for col in trained_columns]

        X_val_copy = pd.DataFrame(0, index=X_val_full.index, columns=trained_columns)
        for col in trained_columns:
            if col in X_val_full.columns:
                X_val_copy[col] = X_val_full[col]
            else:
                log.write("[WARNING] Column '{}' not found in validation data. It will remain zero.\n".format(col))
        return X_val_copy

# === Parameters ===
model_folder = '/_full_path_in_your_server_to_/models'
#dummy dataset
#validation_data_path = '/_full_path_in_your_server_to_/dummy_validation_dataset.csv'
#held out evaluation dataset - terrestrial -234
validation_data_path = '_full_path_in_your_server_to_/cc_terrestrial_evaluation_combined_super_vector_files.csv'
#held out evaluation dataset - aquatic - 704
#validation_data_path = '_full_path_in_your_server_to_/cc_aquatic_evaluation_combined_super_vector_files.csv'
#held out evaluation dataset - combined - 938
#validation_data_path = '_full_path_in_your_server_to_/cc_combined_evaluation_combined_super_vector_files.csv'

output_dir = '/_full_path_in_your_server_to_/output_directory'
debug_log_file = os.path.join(output_dir, 'output_log.txt')
#dummy threshold nr
#thr_number = 99
#terrestrial threshold nr (234-1)
thr_number = 233
#aquatic threshold nr (704-1)
#thr_number = 703
#combined threshold nr (938-1)
#thr_number = 937
threshold_range = np.linspace(0, 1, num=thr_number).tolist()


# Explicitly add 0.5 threshold
if 0.5 not in threshold_range:
    threshold_range.append(0.5)
threshold_range = sorted(threshold_range)  # Ensure the threshold list is sorted

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

output_file_individual = os.path.join(output_dir, 'evaluation_metrics_table_with_thresholds.tsv')
output_file_averaged = os.path.join(output_dir, 'evaluation_metrics_table_averaged_with_thresholds.tsv')

# Corrected header for individual and averaged files
header_individual = "model\tmodel_nr\tdataset\tk\tn_repeats\tthreshold\taccuracy\tprecision\trecall\tspecificity\tf1\ttp\ttn\tfp\tfn\n"
header_averaged = "model\tdataset\tk\tn_repeats\tthreshold\taccuracy\tprecision\trecall\tspecificity\tf1\ttp\ttn\tfp\tfn\n"

# Write headers if files don't exist or are empty
for file_path, header in [(output_file_individual, header_individual), (output_file_averaged, header_averaged)]:
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        with open(file_path, 'w') as f:
            f.write(header)

data = pd.read_csv(validation_data_path)
X_val_full = data.drop(columns=['cc', 'Study'])
y_val = data['cc']

# === Logging ===
debug_log = open(debug_log_file, 'w')

# === Prepare averaging dict ===
threshold_metrics_dict = {}  # key: threshold, value: list of dicts

models = [f for f in os.listdir(model_folder) if f.endswith('.pkl')]
for model_file in sorted(models):
    print("Evaluating model: {}".format(model_file))
    debug_log.write("Evaluating model: {}\n".format(model_file))

    # Extract model identifier (without "model1_" prefix)
    match = re.search(r'repeat(\d+)_fold(\d+)', model_file)
    if match:
        rep = match.group(1)
        fold = match.group(2)
        model_nr = "fold{}_rep{}".format(fold, rep)
    else:
        model_nr = "unknown_model"

    with open(os.path.join(model_folder, model_file), 'rb') as f:
        model_info = pickle.load(f)

    if 'columns' not in model_info:
        print("Skipping model (columns missing): {}".format(model_file))
        debug_log.write("Skipping model (columns missing): {}\n".format(model_file))
        continue

    model = model_info['model']
    trained_columns = model_info['columns']

    X_val_aligned = align_columns(X_val_full, trained_columns)
    model_name = 'logistic_regression'
    dataset_name = os.path.splitext(os.path.basename(validation_data_path))[0]

    for threshold in threshold_range:
        y_proba = model.predict_proba(X_val_aligned)[:, 1]
        y_pred = (y_proba >= threshold).astype(int)

        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, zero_division=0)
        recall = recall_score(y_val, y_pred, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(y_val, y_pred).ravel()
        specificity = float(tn) / (tn + fp) if (tn + fp) > 0 else 0
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0

        # Write to individual file
        with open(output_file_individual, 'a') as f:
            f.write(
                "{}\t{}\t{}\t{}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\n".format(
                    model_name, model_nr, dataset_name, 5, 1, threshold,
                    accuracy, precision, recall, specificity, f1, tp, tn, fp, fn
                )
            )

        # Store in dict for averaging later
        if threshold not in threshold_metrics_dict:
            threshold_metrics_dict[threshold] = []

        threshold_metrics_dict[threshold].append({
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'specificity': specificity,
            'f1': f1,
            'tp': tp,
            'tn': tn,
            'fp': fp,
            'fn': fn
        })

    print("Finished evaluation for {}".format(model_file))
    debug_log.write("Finished evaluation for {}\n".format(model_file))

# === Averaging by threshold ===
for threshold in sorted(threshold_metrics_dict.keys()):  # Sorting thresholds in ascending order
    metric_list = threshold_metrics_dict[threshold]
    avg_metrics = {}
    for key in metric_list[0]:
        avg_metrics[key] = statistics.mean([m[key] for m in metric_list])

    # Write averaged metrics to the output file, excluding the model_nr column
    with open(output_file_averaged, 'a') as f:
        f.write(
            "{}\t{}\t{}\t{}\t{}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.3f}\t{:.0f}\t{:.0f}\t{:.0f}\t{:.0f}\n".format(
                'logistic_regression_avg',  # Model name (constant for averaging)
                dataset_name,
                5,  # Assuming 'k' and 'n_repeats' are constant
                1,  # Assuming 'k' and 'n_repeats' are constant
                threshold,
                avg_metrics['accuracy'],
                avg_metrics['precision'],
                avg_metrics['recall'],
                avg_metrics['specificity'],
                avg_metrics['f1'],
                avg_metrics['tp'],
                avg_metrics['tn'],
                avg_metrics['fp'],
                avg_metrics['fn']
            )
        )

print("Averaged metrics per threshold written to: {}".format(output_file_averaged))
debug_log.write("Averaged metrics per threshold written to: {}\n".format(output_file_averaged))
debug_log.close()
