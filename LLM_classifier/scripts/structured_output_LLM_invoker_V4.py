#!/usr/bin/python3.5

import requests
import json
from pathlib import Path
import sys
import io
from collections import OrderedDict

# Reconfigure sys.stdout to use UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


#Note: please update this URL to your own ollama server endpoint and port
OLLAMA_API_URL = "http://localhost:11434"

def ask_question(model_name, prompt):
    """Sends a structured prompt to the model and ensures JSON response."""
    url = "{}/api/generate".format(OLLAMA_API_URL)
    headers = {"Content-Type": "application/json"}

    # Enforce structured JSON response
    structured_prompt = "{}\n\nPlease provide your response in JSON format with the following structure:\n{{\n    \"explanation\": \"<short explanation>\",\n    \"answer\": \"<***yes*** or ***no***>\"\n}}\nOnly return a valid JSON object.".format(prompt)

    payload = {
        "model": model_name,
        "prompt": structured_prompt,
        "format": "json"  # Enforce JSON output from the model
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()  # Raise an HTTPError for bad responses
    except requests.RequestException as e:
        print("Request error: {}".format(e))
        return {"error": "Request failed."}

    full_response = ""
    for line in response.iter_lines():
        if line:
            try:
                response_data = json.loads(line.decode('utf-8'))
                full_response += response_data.get('response', '')
                if response_data.get('done', False):
                    break
            except json.JSONDecodeError as e:
                print("Error decoding JSON: {}. Response line: {}".format(e, line.decode('utf-8')))
                return {"error": "Invalid JSON response from model"}

    if not full_response:
        print("Empty response from the model.")
        return {"error": "Empty response from model"}

    try:
        parsed_response = json.loads(full_response)  # Ensure response is valid JSON
        if isinstance(parsed_response, dict) and "explanation" in parsed_response and "answer" in parsed_response:
            return OrderedDict([
                ("explanation", parsed_response["explanation"]),
                ("answer", parsed_response["answer"])
            ])
        else:
            return {"error": "Unexpected JSON structure from model"}
    except json.JSONDecodeError as e:
        print("Failed to parse final response as JSON: {}".format(e))
        return {"error": "Invalid JSON response from model"}

def process_studies(prompts_file_path, studies_file_path, model_name, output_file_path):
    """Processes studies and saves JSON responses."""
    
    with prompts_file_path.open('r', encoding='utf-8') as prompts_file:
        prompts = [line.strip() for line in prompts_file]
    
    results = []  # List to store structured output
    
    with studies_file_path.open('r', encoding='utf-8') as input_file:
        for prompt in prompts:
            for line in input_file:
                study_txt = line.strip()
                study_id = line.split("\t")[0]
                
                final_prompt = "{}\nText: {}".format(prompt.split("\t")[1], study_txt)
                response_json = ask_question(model_name, final_prompt)
                
                results.append(OrderedDict([
                    ("Study_ID", study_id),
                    ("Prompt", prompt),
                    ("Response", response_json)
                ]))
            
            input_file.seek(0)  # Reset file cursor
    
    with output_file_path.open('w', encoding='utf-8') as output_file:
        json.dump(results, output_file, indent=4, ensure_ascii=False)
    
    print("JSON output saved to: {}".format(output_file_path))

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Error: Expected 4 arguments (model_name, prompts_file, studies_file, output_file).")
        print("Usage: python structured_output_LLM_invoker_V4.py <model_name> <prompts_file> <studies_file> <output_file>")
        sys.exit(1)

    model_name = sys.argv[1]
    prompts_file_path = Path(sys.argv[2])
    studies_file_path = Path(sys.argv[3])
    output_file_path = Path(sys.argv[4])

    if not prompts_file_path.exists():
        print("Error: Prompts file does not exist: {}".format(prompts_file_path))
        sys.exit(1)

    if not studies_file_path.exists():
        print("Error: Studies file does not exist: {}".format(studies_file_path))
        sys.exit(1)

    if not output_file_path.parent.exists():
        print("Error: Output directory does not exist: {}".format(output_file_path.parent))
        sys.exit(1)

    process_studies(prompts_file_path, studies_file_path, model_name, output_file_path)
