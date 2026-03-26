import os, django, requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project1.settings')
django.setup()

from coding_challenge.judge0 import run_single_case, JUDGE0_URL, HEADERS

java_code = """
import java.util.*;

public class Main {
    public static void main(String[] args) {
        System.out.println("0 1");
    }
}
"""

print('Testing URL:', JUDGE0_URL)
try:
    res = run_single_case(java_code, 62, "2 7 11 15\n9")
    print('Response:', res)
except Exception as e:
    print('Exception:', e)
