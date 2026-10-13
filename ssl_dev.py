"""כיבוי אימות SSL לפיתוח מקומי בלבד (למשל מאחורי סינון רשת שמחליף תעודות).

כבוי כברירת מחדל. להפעלה, הגדירו בקובץ .env:
    DISABLE_SSL_VERIFY=1

אזהרה: אין להפעיל בסביבת ייצור. כיבוי האימות חושף את התקשורת להאזנה.
"""
import os
import ssl

import httpx


def apply_if_enabled() -> bool:
    if os.environ.get("DISABLE_SSL_VERIFY", "").strip().lower() not in ("1", "true", "yes"):
        return False

    class _NoVerifyClient(httpx.Client):
        def __init__(self, *args, **kwargs):
            kwargs["verify"] = False
            super().__init__(*args, **kwargs)

    class _NoVerifyAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["verify"] = False
            super().__init__(*args, **kwargs)

    httpx.Client = _NoVerifyClient
    httpx.AsyncClient = _NoVerifyAsyncClient
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ["PYTHONHTTPSVERIFY"] = "0"
    os.environ["CURL_CA_BUNDLE"] = ""
    print("אזהרה: אימות SSL כבוי (DISABLE_SSL_VERIFY=1). לפיתוח מקומי בלבד.")
    return True