import os
import requests
from openai import OpenAI

default_model = "dall-e-2"
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)
number_of_images_generated_const = 9


def download_image(url, image_number):
    r = requests.get(url, allow_redirects=True)
    open(f"images/image_{image_number}.png", 'wb').write(r.content)


def generate_images(prompt: str, number_of_images_generated: int):
    for i in range(number_of_images_generated):
        response = client.images.generate(
            model="dall-e-2",
            prompt=prompt,
            response_format="url",
            quality="standard"
        )
        download_image(response.data[0].url, i + 1)


if __name__ == '__main__':
    prompt = input("Enter a prompt: ")
    if prompt:
        generate_images(prompt, number_of_images_generated_const)
    else:
        "No prompt entered"
