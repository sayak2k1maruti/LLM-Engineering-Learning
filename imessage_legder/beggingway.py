from typing import Dict, Optional
import logging
import requests
logger = logging.getLogger(__name__)

def _generate_prompt(message: str) -> str:
    return f"""Extract the following transaction information from the message:
- amount: The monetary amount (e.g., $50.00, 50 USD)
- date: The date in YYYY-MM-DD format
- time: The time in HH:MM:SS format (24-hour)
- vendor: The name of the merchant/vendor/store
- transaction_number: The transaction ID or reference number

If any field is not found, use null for that field.

Message: {message}"""
def get_llm_response(message: str) -> Optional[Dict]:
    try:
        payload = {
            "model": "llama3.2",
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ],
            "format": {
                "type": "object",
                "properties": {
                    "amount": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "vendor": {"type": "string"},
                    "transaction_number": {"type": "string"}
                },
                "required": ["amount", "date", "time", "vendor", "transaction_number"]
            },
            "stream": False
        }
        
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=payload,
        )
        if response.status_code != 200:
            logger.error(f"Request failed with status code {response.status_code}")
            return None
        
        result = response.json()
        return result.get("message", {}).get("content")
    except Exception as e:
        logger.error(f"Error: {e}")
        return None



def main():
    message = input("Message: ")
    prompt = _generate_prompt(message)
    response = get_llm_response(prompt)
    if response:
        try:
            # Try to parse as JSON
            import json
            data = json.loads(response)
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("Raw response:")
            print(response)
    else:
        print("Failed to get response")


if __name__ == "__main__":
    main()
