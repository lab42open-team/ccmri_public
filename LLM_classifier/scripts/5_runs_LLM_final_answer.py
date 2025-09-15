import os
import sys
import csv

def add_final_answer(output_dir):
    if not os.path.isdir(output_dir):
        print("Error: Directory does not exist:", output_dir)
        sys.exit(1)

    input_tsv = None
    for filename in os.listdir(output_dir):
        if filename.endswith("aggregated_results.tsv"):
            input_tsv = os.path.join(output_dir, filename)
            break
    
    if input_tsv is None:
        print("Error: No file ending with 'aggregated_results.tsv' found in the directory:", output_dir)
        sys.exit(1)

    base_filename = os.path.basename(input_tsv)
    parts = base_filename.split("_")
    
    if len(parts) >= 3:
        model_prompt_part = "_".join(parts[:-2])
    else:
        model_prompt_part = "unknown_model_prompt"

    with open(input_tsv, "r") as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        rows = list(reader)

    run_columns = ["Models_answer_run1", "Models_answer_run2", "Models_answer_run3", "Models_answer_run4", "Models_answer_run5"]
    if not all(col in reader.fieldnames for col in run_columns):
        print("Error: The input file does not have the required run columns.")
        sys.exit(1)

    for row in rows:
        yes_count = 0
        for i in range(5):
            if row[run_columns[i]].strip().lower() == "yes":
                yes_count += 1

        # Add final_answer(N) columns
        for threshold in [3, 4, 5]:
            col_name = "final_answer(" + str(threshold) + ")"
            if yes_count >= threshold:
                row[col_name] = "yes"
            else:
                row[col_name] = "no"

    # New fieldnames with added final_answer columns
    new_fields = reader.fieldnames + ["final_answer(3)", "final_answer(4)", "final_answer(5)"]
    output_filename = model_prompt_part + "_aggregated_results_with_final_answer.tsv"
    output_tsv = os.path.join(output_dir, output_filename)

    with open(output_tsv, "w", newline='') as tsvfile:
        writer = csv.DictWriter(tsvfile, fieldnames=new_fields, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    print("TSV file with final_answer(3/4/5) columns created:", output_tsv)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python 5_runs_final_answer.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]
    add_final_answer(output_dir)
