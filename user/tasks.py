# myapp/tasks.py

from celery import shared_task
import time
import os

HF_API_URL = os.getenv("HF_API_URL")
HF_API_KEY = os.getenv("HF_API_KEY")

@shared_task(bind=True)
def query_huggingface(self, prompt, retries=3, timeout=200):

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {HF_API_KEY}"
    }

    data = {"inputs": prompt}

    for attempt in range(retries):
        try:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=data,
                timeout=timeout
            )

            if response.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                return f"Hugging Face API error: {response.status_code} - {response.text}"

            result = response.json()

            if isinstance(result, list) and "generated_text" in result[0]:
                raw_output = result[0]["generated_text"]
                return raw_output
            else:
                return result

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                return f"Hugging Face API request failed after {retries} attempts: {str(e)}"