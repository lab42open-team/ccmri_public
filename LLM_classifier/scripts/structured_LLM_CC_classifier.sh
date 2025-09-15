#!/bin/bash

# Get the current date and time in the desired format
LOGFILE="_full_path_in_your_server_to_/logfiles/output_$(date '+%Y-%m-%d_%H-%M-%S').log"

# Redirect both stdout and stderr to the log file
exec > >(tee -a "$LOGFILE") 2>&1

# Capture the start time
start_time=$(date +%s)

# Define models and prompts arrays
models=("phi4:14b-q8_0" "llama3.1:8b-instruct-q8_0" "qwen2.5:14b-instruct-q8_0" "llama3.3:70b-instruct-q8_0" "qwen2.5:72b-instruct-q8_0" "qwen2.5:32b-instruct-q8_0" "mistral-small:22b-instruct-2409-q8_0" "mistral-nemo:12b-instruct-2407-q8_0")
#"phi4:14b-q8_0" "llama3.1:8b-instruct-q8_0" "qwen2.5:14b-instruct-q8_0" "llama3.3:70b-instruct-q8_0" "qwen2.5:72b-instruct-q8_0" "qwen2.5:32b-instruct-q8_0" "mistral-small:22b-instruct-2409-q8_0" "mistral-nemo:12b-instruct-2407-q8_0"
#prompts=("/_full_path_in_your_server_to_/prompts/prompt4.tsv" "/_full_path_in_your_server_to_/prompts/prompt5.tsv")
prompts=("/_full_path_in_your_server_to_/prompts/prompt4.tsv" "/_full_path_in_your_server_to_/prompts/prompt5.tsv")



# Define dataset path
#dataset="/_full_path_in_your_server_to_/datasets/held_out_evaluation_set/combined_held_out.tsv"
#dataset="/_full_path_in_your_server_to_/datasets/held_out_evaluation_set/aquatic_held_out.tsv"
dataset="/_full_path_in_your_server_to_/datasets/held_out_evaluation_set/terrestrial_held_out.tsv"

# Loop through each model and prompt
for model_choice in "${models[@]}"; do
    model_start_time=$(date +%s)  # Start time for the model

    for prompt in "${prompts[@]}"; do
        for run in {1..5}; do
            run_start_time=$(date +%s)  # Start time for the run

            # Generate filenames
            model_base=$(basename "$model_choice" | tr ':' '_')  # Replace ':' with '_'
            prompt_base=$(basename "$prompt" .tsv)

            # Create a directory for the model and prompt combination if it doesn't exist
            output_dir="/_full_path_in_your_server_to_/results/held_out_evaluation/${model_base}_${prompt_base}"
            mkdir -p "$output_dir"  # Create the directory if it doesn't exist

            output="$output_dir/LLM_output_${model_base}_${prompt_base}_run_${run}.json"
            #metrics_output="$output_dir/metrics_LLM_output_${model_base}_${prompt_base}_run_${run}.tsv"

            # Execute scripts
            echo "Running model: $model_choice with prompt: $prompt (Run $run)"
            /usr/bin/python3 ./structured_output_LLM_invoker_V4.py "$model_choice" "$prompt" "$dataset" "$output"


            # Capture runtime per run
            run_end_time=$(date +%s)
            run_duration=$((run_end_time - run_start_time))
            run_minutes=$((run_duration / 60))
            run_seconds=$((run_duration % 60))
            echo "Model: $model_choice | Run $run completed in $run_minutes min $run_seconds sec" >> "$LOGFILE"

        done
        #here
        # After processing all runs for a model-prompt combination, aggregate results into a TSV file
        echo "Aggregating results for $output_dir..."
        /usr/bin/python3 ./5_runs_LLM_summarizer.py "$output_dir"
        # Now getting the final yes/no answer from 5 runs
        echo "Getting the final yes/no answer from 5 runs for $output_dir..."
        /usr/bin/python3 ./5_runs_LLM_final_answer.py "$output_dir"
        # Now calculating metrics from the 5 runs
        echo "Getting metrics for $output_dir..."
        /usr/bin/python3 ./5_runs_LLM_metrics.py "$output_dir"


        
    done

    # Capture total runtime per model
    model_end_time=$(date +%s)
    model_duration=$((model_end_time - model_start_time))
    model_hours=$((model_duration / 3600))
    model_minutes=$(( (model_duration % 3600) / 60 ))
    model_seconds=$((model_duration % 60))
    echo "Model: $model_choice | Total runtime for 5 runs: $model_hours hours $model_minutes min $model_seconds sec" >> "$LOGFILE"
done

# Capture total script execution time
end_time=$(date +%s)
duration=$((end_time - start_time))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$((duration % 60))

echo "Script execution completed in $hours hours, $minutes minutes, and $seconds seconds." >> "$LOGFILE"
