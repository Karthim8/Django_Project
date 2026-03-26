import os, django, requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from coding_challenge.judge0 import HEADERS, JUDGE0_URL

java_code = """
import java.util.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("0 1");
    }
}
"""

print('URL:', JUDGE0_URL)
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
