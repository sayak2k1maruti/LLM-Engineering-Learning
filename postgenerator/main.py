import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
open_ai_client = OpenAI()
def _create_prompt(topic: str) -> str:
    """
    Create a prompt by loading the template and formatting it with the topic and examples.
    """
    # Load the prompt template
    with open("prompt.md", "r") as f:
        prompt_template = f.read()

    # Load examples from JSON
    with open("examples.json", "r") as f:
        examples = json.load(f)

    # Format examples into a readable string
    examples_text = ""
    if examples:
        formatted_examples = []
        for example in examples:
            formatted_examples.append(
                f"**Topic:** {example['topic']}\n**Generated Post:** {example['generated-post']}"
            )
        examples_text = "\n\n".join(formatted_examples)

    # Format the prompt with topic and examples
    formatted_prompt = prompt_template.format(
        topic=topic,
        examples=examples_text
    )

    return formatted_prompt

def generate_post(user_input) -> str:
    """
    Call the OpenAI API to generate a post based on the user_input
    """

    response = open_ai_client.responses.create(
        model="gpt-5.4-mini",
        input=_create_prompt(user_input)
    )

    # payload = {
    #     "model": "gpt-5.4-mini",
    #     "input":
    # }
    # response = requests.post(
    #     "https://api.openai.com/v1/responses",
    #     json = payload,
    #     headers={
    #         "Content-Type": "application/json",
    #         "Authorization": f"Bearer {OPEN_AI_API_KEY}"
    #     }

    # )
    # if response.status_code != 200:
    #     print("Error:", response.status_code, response.text)
    #     return "Failed to generate post."
    # return response.json().get("output", [{},])[0].get("content",[{},])[0].get("text", "No content generated...")
    #
    return response.output_text

def main():
    user_input = input("What should be the post about? ")
    post = generate_post(user_input)
    print("Generated X Post: ")
    print(post)

if __name__ == "__main__":
    main()
