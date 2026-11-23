import threading
import time

import requests

from config import API_URL, PAGE_URL, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, VERIFY_TLS


HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.lotacor.pt",
    "Referer": PAGE_URL,
    "X-Requested-With": "XMLHttpRequest"
}

_thread_local = threading.local()


def get_session():
    """Create and reuse one HTTP session per worker thread."""

    if not hasattr(_thread_local, "session"):
        session = requests.Session()
        session.headers.update(HEADERS)

        response = session.get(PAGE_URL, verify=VERIFY_TLS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        _thread_local.session = session

    return _thread_local.session


def query_lotacor(start_date, final_date, query_type="DNA", lota_id="all",
                  fao="all", ilha_id="all"):
    """Retrieve species data for a requested date interval."""

    payload = {
        "type": query_type, "lota_id": lota_id, "fao": fao,
        "ilha_id": ilha_id, "start_date": start_date,
        "final_date": final_date, "day_date": ""
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            session = get_session()
            response = session.post(API_URL, data=payload, verify=VERIFY_TLS,
                                    timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            if not response.text.strip():
                raise ValueError("Empty API response. Check the session and request.")

            result = response.json()
            if not isinstance(result, list):
                raise ValueError("Unexpected API response: expected a JSON list.")

            return result

        except (requests.RequestException, ValueError) as error:
            if attempt == MAX_RETRIES:
                raise

            print("Request failed ({}/{}): {}".format(attempt, MAX_RETRIES, error))
            time.sleep(RETRY_DELAY * attempt)

    return []
