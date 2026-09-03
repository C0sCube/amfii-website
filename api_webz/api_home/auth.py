import math, os
import requests
from pathlib import Path
current_file = Path(__file__).resolve()
# .parent gets 'app', and the next .parent gets 'root'
ROOT_DIR = current_file.parent.parent
os.chdir(ROOT_DIR)


from constants import AUTH_UTILS

_auth_ = AUTH_UTILS

# LDAP API URLs
AUTH_API_URL = _auth_["AUTH_API_URL"]
CREATE_API_URL = _auth_["CREATE_API_URL"]
CHANGE_PASS_API_URL = _auth_["CREATE_API_URL"]
USER_EXIST = _auth_["USER_EXIST"]


def authenticate_user(username, password):
    """Authenticate user with LDAP API"""
    try:
        payload = {"username": username, "password": password}
        response = requests.post(AUTH_API_URL, json=payload, verify=False)

        if response.status_code == 200:
            return response.json()  # Successful login, returns user details or token
        else:
            return {"error": "Authentication failed", "details": response.json()}
    except Exception as e:
        return {"error": f"Authentication error: {str(e)}"}


def sanitize_payload(payload):
    """Replace NaN or None values with empty strings"""
    return {
        k: ("" if (v is None or (isinstance(v, float) and math.isnan(v))) else v)
        for k, v in payload.items()
    }


def is_user_exist(username):
    try:
        response = requests.get(f"{USER_EXIST}{username}", verify=False)
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f"User existence check failed: {e}")
        return False


def change_password(username, old_password, new_password):
    """Change user password with LDAP API"""
    try:
        payload = {"username": username, "newPassword": new_password, "type": 0}
        response = requests.post(CHANGE_PASS_API_URL, json=payload)

        if response.status_code == 200:
            return {"message": "Password changed successfully"}
        else:
            return {"error": "Password change failed", "details": response.json()}
    except Exception as e:
        return {"error": f"Password change error: {str(e)}"}
