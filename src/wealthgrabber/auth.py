import getpass
from typing import Optional

import keyring
from ws_api import (
    LoginFailedException,
    OTPRequiredException,
    WealthsimpleAPI,
    WSAPISession,
)

# Constants
KEYRING_SERVICE = "wealthsimple-account-viewer"


def _persist_session(session_json, username):
    """Save session to keyring"""
    keyring.set_password(f"{KEYRING_SERVICE}.{username}", "session", session_json)


def _get_username(username: Optional[str] = None, verbose: bool = False) -> str:
    """Get username from user, using cached email if available."""
    # If username is explicitly provided, use it
    if username:
        return username

    # Otherwise, try cached email
    cached_email = keyring.get_password(KEYRING_SERVICE, "last_email")
    if cached_email:
        if verbose:
            print(f"Using cached email: {cached_email}")
        return cached_email

    # No cached email, prompt for one
    username = input("Wealthsimple username (email): ")
    return username


def _try_restore_session(
    username: str, verbose: bool = False
) -> Optional[WealthsimpleAPI]:
    """Try to restore an existing session from keyring. Returns None if not available/invalid."""
    session_json = keyring.get_password(f"{KEYRING_SERVICE}.{username}", "session")
    if not session_json:
        return None

    try:
        session = WSAPISession.from_json(session_json)
        if verbose:
            print("✓ Found existing session, attempting to use it...")
        ws = WealthsimpleAPI.from_token(session, _persist_session, username)
        ws.get_accounts()  # Test the session
        if verbose:
            print("✓ Session is valid")
        return ws
    except Exception as e:
        if verbose:
            print(f"Existing session expired or invalid: {e}")
        return None


def _perform_login(username: str, verbose: bool = False) -> Optional[WealthsimpleAPI]:
    """Handle the login flow with OTP support. Returns authenticated client or None on failure."""
    password = None
    otp_answer = None

    while True:
        try:
            if not password:
                password = getpass.getpass("Password: ")

            WealthsimpleAPI.login(
                username, password, otp_answer, persist_session_fct=_persist_session
            )

            session_json = keyring.get_password(
                f"{KEYRING_SERVICE}.{username}", "session"
            )
            session = WSAPISession.from_json(session_json)
            ws = WealthsimpleAPI.from_token(session, _persist_session, username)
            if verbose:
                print("✓ Successfully authenticated")

            # Cache the email after successful login
            keyring.set_password(KEYRING_SERVICE, "last_email", username)

            return ws

        except OTPRequiredException:
            otp_answer = input("Two-factor authentication code: ")
        except LoginFailedException:
            print("✗ Login failed. Try again.")
            password = None
            otp_answer = None
        except Exception as e:
            print(f"✗ An unexpected error occurred: {e}")
            return None


def get_authenticated_client(
    force_login: bool = False, username: Optional[str] = None, verbose: bool = False
) -> Optional[WealthsimpleAPI]:
    """
    Handle login with session persistence.
    Returns a WealthsimpleAPI instance or None if login failed/aborted.

    Args:
        force_login: If True, force a new login even if a valid session exists.
        username: Optional email to use. If not provided, uses cached email or prompts.
        verbose: If True, print status messages during authentication.
    """
    username = _get_username(username, verbose=verbose)

    if not force_login:
        ws = _try_restore_session(username, verbose=verbose)
        if ws:
            return ws

    if verbose:
        print("Creating new session...")
    return _perform_login(username, verbose=verbose)


def logout(username: Optional[str] = None, clear_email: bool = False) -> None:
    """
    Clear stored session and optionally cached email.

    Args:
        username: Email to clear session for. If None, uses cached email.
        clear_email: If True, also clear the cached email.
    """
    # Get username to clear
    if username is None:
        username = keyring.get_password(KEYRING_SERVICE, "last_email")
        if not username:
            print("No cached session found.")
            return

    # Clear session for this username
    session_key = f"{KEYRING_SERVICE}.{username}"
    try:
        keyring.delete_password(session_key, "session")
        print(f"✓ Cleared session for {username}")
    except keyring.errors.PasswordDeleteError:
        print(f"No session found for {username}")

    # Optionally clear cached email
    if clear_email:
        try:
            keyring.delete_password(KEYRING_SERVICE, "last_email")
            print("✓ Cleared cached email")
        except keyring.errors.PasswordDeleteError:
            pass
