import os
import sys
import csv
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

def load_data(results_file, true_answers_file, answer_column):
    results = {}
    with open(results_file, 'r') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            # Convert 'yes' to 1 and 'no' to 0
            if row.get(answer_column) is None:
                continue  # Skip if this column doesn't exist
            final_answer = 1 if row[answer_column].strip().lower() == 'yes' else 0
            results[row['Study_id']] = final_answer

    true_answers = {}
    with open(true_answers_file, 'r') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            true_answer = 1 if row['CC_related'].strip().lower() == 'yes' else 0
            true_answers[row['Study_id']] = true_answer

    return results, true_answers

def calculate_metrics(y_true, y_pred):
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) != 0 else 0
    return accuracy, precision, recall, f1, specificity

def get_final_answer_file(output_dir):
    for filename in os.listdir(output_dir):
        if filename.endswith('_aggregated_results_with_final_answer.tsv'):
            return os.path.join(output_dir, filename)
    return None

def extract_model_prompt_from_filename(filename):
    base_name = os.path.basename(filename)
    parts = base_name.split('_')
    if len(parts) >= 2:
        return parts[0] + '-' + parts[1]
    else:
        return 'unknown-model-prompt'

def main():
    if len(sys.argv) != 2:
        print("Usage: python 5_runs_LLM_metrics.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    final_answer_file = get_final_answer_file(output_dir)

    if final_answer_file is None:
        print("Error: No file ending with '_aggregated_results_with_final_answer.tsv' found in directory:", output_dir)
        sys.exit(1)

    true_answers_file = '/_full_path_in_your_server_to_/held_out_evaluation_set_aquatic.tsv'

    thresholds = [3, 4, 5]
    summary_metrics = []

    model_prompt_combo = extract_model_prompt_from_filename(final_answer_file)

    for threshold in thresholds:
        answer_column = 'final_answer({})'.format(threshold)
        results, true_answers = load_data(final_answer_file, true_answers_file, answer_column)

        y_true = []
        y_pred = []
        for study_id in results:
            if study_id in true_answers:
                y_true.append(true_answers[study_id])
                y_pred.append(results[study_id])

        if not y_true or not y_pred:
            print("Warning: No overlapping study IDs between predictions and ground truth for threshold {}".format(threshold))
            continue

        accuracy, precision, recall, f1, specificity = calculate_metrics(y_true, y_pred)

        # Print to console
        print("\nMetrics for final_answer({}/5 yeses):".format(threshold))
        print("Accuracy: {:.4f}".format(accuracy))
        print("Precision: {:.4f}".format(precision))
        print("Recall: {:.4f}".format(recall))
        print("Specificity: {:.4f}".format(specificity))
        print("F1 Score: {:.4f}".format(f1))

        # Save to individual threshold metrics file
        output_metrics_file = os.path.join(output_dir, '{}_final_answer_{}_metrics.tsv'.format(model_prompt_combo, threshold))
        with open(output_metrics_file, 'w', newline='') as tsvfile:
            writer = csv.writer(tsvfile, delimiter='\t')
            writer.writerow(['accuracy', 'precision', 'recall', 'specificity', 'f1_score'])
            writer.writerow([accuracy, precision, recall, specificity, f1])

        # Append to summary list
        summary_metrics.append([threshold, accuracy, precision, recall, specificity, f1])

    # Write summary file
    summary_file = os.path.join(output_dir, '{}_summary_threshold_metrics.tsv'.format(model_prompt_combo))
    with open(summary_file, 'w', newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')
        writer.writerow(['threshold', 'accuracy', 'precision', 'recall', 'specificity', 'f1_score'])
        for row in summary_metrics:
            writer.writerow(row)

    print("\nSummary metrics saved to: {}".format(summary_file))

if __name__ == "__main__":
    main()
