import os
import sys
import json
import csv

def aggregate_json_to_tsv(json_dir):
    # Ensure the directory exists
    if not os.path.isdir(json_dir):
        print("Error: Directory does not exist:", json_dir)
        sys.exit(1)

    # Find all JSON files in the directory
    json_files = sorted([f for f in os.listdir(json_dir) if f.endswith(".json")])

    if not json_files:
        print("Error: No JSON files found in", json_dir)
        sys.exit(1)

    # Derive model and prompt from the directory name
    dir_name = os.path.basename(json_dir)
    parts = dir_name.split('_')  # Assuming underscores separate model and prompt details
    if len(parts) >= 2:
        model_base = "_".join(parts[:-1])  # All but the last part will be the model base
        prompt_base = parts[-1]  # The last part will be the prompt base
    else:
        model_base = "unknown_model"
        prompt_base = "unknown_prompt"

    # Define output TSV file path with model and prompt combination in filename
    output_tsv = os.path.join(json_dir, model_base + "_" + prompt_base + "_aggregated_results.tsv")

    # Dictionary to store results by Study ID
    results = {}

    # Process each JSON file
    for i, json_file in enumerate(json_files):
        file_path = os.path.join(json_dir, json_file)

        with open(file_path, "r") as f:
            data = json.load(f)

        for entry in data:
            # Get Study_ID and the answer field (clean the answer by removing '***' and keep only 'yes' or 'no')
            study_id = entry.get("Study_ID", "UNKNOWN")  # Ensure you use the correct key name
            answer = entry.get("Response", {}).get("answer", "N/A").strip("*").lower()  # Strip the '***' and lower case answer

            # Only keep 'yes' or 'no', else set it as 'N/A'
            if answer not in ['yes', 'no']:
                answer = "N/A"

            if study_id not in results:
                results[study_id] = []

            results[study_id].append(answer)

    # Write to TSV file
    with open(output_tsv, "w", newline='') as tsvfile:
        writer = csv.writer(tsvfile, delimiter='\t')

        # Write header with dynamic columns for each run
        headers = ["Study_id"] + ["Models_answer_run{}".format(i+1) for i in range(len(json_files))]
        writer.writerow(headers)

        # Write rows with study_id and answers for each run
        for study_id, answers in results.items():
            writer.writerow([study_id] + answers)

    print("TSV file created:", output_tsv)

if __name__ == "__main__":
    # Ensure exactly one argument (JSON directory) is provided
    if len(sys.argv) != 2:
        print("Usage: python aggregate_json_to_tsv.py <json_directory>")
        sys.exit(1)

    json_directory = sys.argv[1]
    aggregate_json_to_tsv(json_directory)
