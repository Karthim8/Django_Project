import os
import requests

JUDGE0_URL = "https://Judge0-CE.proxy-production.allthingsdev.co/submissions"
HEADERS = {
    "x-apihub-key":      os.getenv("JUDGE0_API_KEY", ""),
    "x-apihub-host":     os.getenv("JUDGE0_API_HOST", "Judge0-CE.allthingsdev.co"),
    "x-apihub-endpoint": os.getenv("JUDGE0_API_ENDPOINT", ""),
    "Content-Type":      "application/json",
}

def run_single_case(source_code: str, language_id: int, stdin: str) -> dict:
    response = requests.post(
        JUDGE0_URL + "?base64_encoded=false&wait=true",
        json={
            "source_code": source_code,
            "language_id": language_id,
            "stdin":       stdin,
        },
        headers=HEADERS,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def judge_submission(submission, language_id=None) -> "Submission":
    test_cases = submission.problem.test_cases
    passed     = 0
    error_msg  = None
    actual_lang = language_id if language_id else submission.problem.language_id

    for tc in test_cases:
        try:
            result = run_single_case(
                submission.source_code,
                actual_lang,
                tc["input"],
            )
            stdout = (result.get("stdout") or "").strip()
            stderr = (result.get("stderr") or "").strip()

            if stderr:
                error_msg = stderr
                break

            if stdout == str(tc["expected"]).strip():
                passed += 1

        except requests.RequestException as e:
            error_msg = str(e)
            break

    total = len(test_cases)
    submission.passed_cases = passed
    submission.total_cases  = total
    submission.score        = int((passed / total) * 100) if total else 0
    submission.status       = "error" if error_msg else ("accepted" if passed == total else "partial")
    submission.save()
    return submission