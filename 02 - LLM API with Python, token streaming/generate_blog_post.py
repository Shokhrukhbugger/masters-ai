import os
from openai import OpenAI

default_model = "gpt-4o-mini"
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


def make_prompt(transcript: str):
    return [
        {"role": "system", "content": "You are a skilled blog post writer."},
        {"role": "user", "content": f"Write a short blog post based on this lecture summary:\n {transcript}"}
    ]


def generate_blog_post(prompt_messages):
    response = client.chat.completions.create(
        model=default_model,
        messages=prompt_messages,
        temperature=0.5
    )

    return response.choices[0].message.content.strip()


# Example usage
if __name__ == "__main__":
    with open("lesson-1-transcript.txt", "r", encoding="utf-8") as file:
        transcript = file.read()

    prompt_messages = make_prompt(transcript)

    # Generate the blog post
    blog_post = generate_blog_post(prompt_messages)

    # Save the used prompt_messages to a workflow.txt
    with open("workflow.txt", "w", encoding="utf-8") as file:
        file.write(str(prompt_messages))

    # Save the blog post to a file
    with open("README.md", "w", encoding="utf-8") as file:
        file.write(blog_post)

    print("Blog post has been generated and saved as 'README.md'.")
