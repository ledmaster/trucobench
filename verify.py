#!/usr/bin/env python3
import os
from litellm import completion

def main():
    # Define directories
    match_history_dir = 'match_history'
    verification_dir = 'verification'
    os.makedirs(verification_dir, exist_ok=True)

    # Read the verifier prompt template from verifier_prompt.txt
    with open('verifier_prompt.txt', 'r', encoding='utf-8') as prompt_file:
        verifier_prompt_template = prompt_file.read()

    # Iterate over each file in the match_history folder
    for filename in os.listdir(match_history_dir):
        file_path = os.path.join(match_history_dir, filename)
        print(file_path)
        if os.path.isfile(file_path):
            # Determine the corresponding verification file path and skip if it exists
            base_name, _ = os.path.splitext(filename)
            output_filename = f"{base_name}_verification.txt"
            output_path = os.path.join(verification_dir, output_filename)
            if os.path.exists(output_path):
                print(f"Verification for {filename} already exists, skipping.")
                continue

            # Open and read the match file content
            with open(file_path, 'r', encoding='utf-8') as match_file:
                match_history_text = match_file.read()

            # Prepare the complete prompt by replacing the placeholder in the template
            prompt = verifier_prompt_template.format(readable_match_history=match_history_text)
            #print(prompt)
            # Send the prompt to the LLM using litellm (adjust the API call if needed)
            messages = [{"role": "user", "content": prompt}]
            response = completion(model='openrouter/openai/o3-mini',
                                  messages=messages)

            verification_output = response.choices[0].message.content

            # Construct the output filename and write the verification answer there
            base_name, _ = os.path.splitext(filename)
            output_filename = f"{base_name}_verification.txt"
            output_path = os.path.join(verification_dir, output_filename)
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(verification_output)

            print(f"Saved verification for {filename} to {output_filename}")

if __name__ == '__main__':
    main()
