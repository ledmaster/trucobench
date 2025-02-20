#!/usr/bin/env python3
import os
import litellm

def main():
    # Define directories
    match_history_dir = 'match_history'
    verification_dir = 'verification'
    os.makedirs(verification_dir, exist_ok=True)

    # Read the verifier prompt template from verifier_prompt.txt
    with open('verifier_prompt.txt', 'r') as prompt_file:
        verifier_prompt_template = prompt_file.read()

    # Iterate over each file in the match_history folder
    for filename in os.listdir(match_history_dir):
        file_path = os.path.join(match_history_dir, filename)
        if os.path.isfile(file_path):
            # Open and read the match file content
            with open(file_path, 'r') as match_file:
                match_history_text = match_file.read()

            # Prepare the complete prompt by replacing the placeholder in the template
            prompt = verifier_prompt_template.format(readable_match_history=match_history_text)

            # Send the prompt to the LLM using litellm (adjust the API call if needed)
            response = litellm.generate(prompt)
            # Use response.text if available; otherwise, cast the response to string
            verification_output = response.text if hasattr(response, 'text') else str(response)

            # Construct the output filename and write the verification answer there
            base_name, _ = os.path.splitext(filename)
            output_filename = f"{base_name}_verification.txt"
            output_path = os.path.join(verification_dir, output_filename)
            with open(output_path, 'w') as output_file:
                output_file.write(verification_output)

            print(f"Saved verification for {filename} to {output_filename}")

if __name__ == '__main__':
    main()
