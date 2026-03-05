# PRO-TIP FOR THE DEMO:
# This is the actual API call that moves your local CSV data to the ABDM Dashboard
def push_to_abdm_gateway(record_details):
    url = "https://dev.abdm.gov.in/gateway/v0.5/links/link/add-care-contexts"
    headers = {"Authorization": "Bearer " + session_token, "X-CM-ID": "sbx"}

    # This 'Notifies' the National Dashboard that a new record exists
    payload = {
        "accessToken": "USER_CONSENT_TOKEN",
        "patient": {
            "referenceNumber": record_details['abha_id'],
            "display": record_details['name'],
            "careContexts": [{
                "referenceNumber": "BLOOD_DONATION_001",
                "display": "O+ Blood Donation at City Clinic"
            }]
        }
    }
    # requests.post(url, json=payload)