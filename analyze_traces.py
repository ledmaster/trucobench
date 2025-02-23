#!/usr/bin/env python3
import os
import json
from litellm import completion

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze a specific match trace file')
    parser.add_argument('filename', help='Name of the match trace file to analyze')
    args = parser.parse_args()

    # Define directories
    match_history_dir = 'match_traces'
    analysis_dir = 'trace_analysis'
    os.makedirs(analysis_dir, exist_ok=True)

    # Read the analyst prompt template from analyst_prompt.txt
    with open('analyst_prompt.txt', 'r', encoding='utf-8') as prompt_file:
        verifier_prompt_template = prompt_file.read()

    file_path = os.path.join(match_history_dir, args.filename)
        print(file_path)
        if os.path.isfile(file_path):
            # Determine the corresponding analysis file path and skip if it exists
            base_name, _ = os.path.splitext(filename)
            output_filename = f"{base_name}_analysis.txt"
            output_path = os.path.join(analysis_dir, output_filename)
            #if os.path.exists(output_path):
            #    print(f"Analysis for {filename} already exists, skipping.")
            #    continue

            # Open and read the match file content, extracting choices content
            extracted_content = []
            with open(file_path, 'r', encoding='utf-8') as match_file:
                for line in match_file:
                    try:
                        data = json.loads(line)
                        if 'response' in data and 'choices' in data['response']:
                            for choice in data['response']['choices']:
                                content = choice['message'].get('content', '')
                                reasoning = choice['message'].get('reasoning')
                                
                                entry = {
                                    'timestamp': data['timestamp'],
                                    'model': data['model'],
                                    'player': data['player'],
                                    'action_type': data['action_type'],
                                    'content': content,
                                    'reasoning': reasoning
                                }
                                extracted_content.append(entry)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse line in {filename}")
                        continue

            # Format the extracted content into readable text
            match_history_text = ""
            for entry in extracted_content:
                match_history_text += f"Time: {entry['timestamp']}\n"
                match_history_text += f"Model: {entry['model']}\n"
                match_history_text += f"Player: {entry['player']}\n"
                match_history_text += f"Action: {entry['action_type']}\n"
                if entry['reasoning']:
                    match_history_text += f"Reasoning: {entry['reasoning']}\n"
                match_history_text += f"Response: {entry['content']}\n"

                match_history_text += "-" * 40 + "\n"

            print(match_history_text)
            # Prepare the complete prompt
            prompt = verifier_prompt_template.format(log=match_history_text)
            # Send the prompt to the LLM using litellm (adjust the API call if needed)
            messages = [{"role": "user", "content": prompt}]
            try:
                response = completion(model='gemini/gemini-2.0-pro-exp-02-05',
                                      temperature=0,
                                    messages=messages)
                analysis_output = response.choices[0].message.content
            except Exception as e:
                print(f"Error getting analysis for {filename}: {str(e)}")
                continue

            # Construct the output filename and write the analysis answer there
            base_name, _ = os.path.splitext(filename)
            output_filename = f"{base_name}_analysis.txt"
            output_path = os.path.join(analysis_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(analysis_output)

            print(f"Saved analysis for {filename} to {output_filename}")

if __name__ == '__main__':
    main()
