import os, django, requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

import os
# Check if key is rapidapi
KEY = os.getenv("JUDGE0_API_KEY", "")
JUDGE0_URL = "https://judge0-ce.p.rapidapi.com/submissions"

java_code = """
import java.util.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("0 1");
    }
}
"""

HEADERS = {
    "X-RapidAPI-Key": KEY,
    "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
    "Content-Type": "application/json",
}

print('Testing RapidAPI URL:', JUDGE0_URL)
try:
    response = requests.post(
        JUDGE0_URL + "?base64_encoded=false&wait=true",
        json={  
            "source_code": java_code,
            "language_id": 62,
            "stdin": "2 7 11 15\n9"
        },
        headers=HEADERS,
        timeout=15,
    )
    print('Status Code:', response.status_code)
    print('Response:', response.text)
except Exception as e:
    print('Exception:', e)
