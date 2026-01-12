from unittest.mock import MagicMock, patch

import pytest

from wealthgrabber.auth import _persist_session, get_authenticated_client, logout


@patch("wealthgrabber.auth.keyring")
def test_persist_session(mock_keyring):
    """Test session persistence calls keyring."""
    _persist_session('{"token": "123"}', "testuser")
    mock_keyring.set_password.assert_called_with(
        "wealthsimple-account-viewer.testuser", "session", '{"token": "123"}'
    )


@patch("wealthgrabber.auth.keyring")
@patch("wealthgrabber.auth.WSAPISession")
@patch("wealthgrabber.auth.WealthsimpleAPI")
@patch("builtins.print")
def test_get_authenticated_client_existing_session(
    mock_print, mock_ws_api, mock_session_cls, mock_keyring
):
    """Test reusing an existing valid session."""
    # First call gets cached email, second call gets session
    mock_keyring.get_password.side_effect = [
        "testuser@example.com",
        '{"valid": "json"}',
    ]

    mock_session = MagicMock()
    mock_session_cls.from_json.return_value = mock_session

    mock_ws = MagicMock()
    mock_ws_api.from_token.return_value = mock_ws

    # Run
    client = get_authenticated_client(force_login=False, verbose=True)

    # Verify
    assert client == mock_ws
    mock_ws.get_accounts.assert_called_once()  # Verify it tested the session
    mock_ws_api.login.assert_not_called()
    # Should print that it's using cached email
    assert any("Using cached email" in str(call) for call in mock_print.call_args_list)


@patch("wealthgrabber.auth.keyring")
@patch("wealthgrabber.auth.WSAPISession")
@patch("wealthgrabber.auth.WealthsimpleAPI")
@patch("builtins.print")
def test_get_authenticated_client_expired_session(
    mock_print, mock_ws_api, mock_session_cls, mock_keyring
):
    """Test behavior when existing session is invalid (should trigger login flow - which we will stop at)."""
    # First call gets cached email, second call gets session
    mock_keyring.get_password.side_effect = [
        "testuser@example.com",
        '{"invalid": "json"}',
    ]

    mock_session = MagicMock()
    mock_session_cls.from_json.return_value = mock_session

    # Mock from_token to raise exception (invalid session)
    mock_ws_api.from_token.side_effect = Exception("Session expired")

    # We want to stop it from entering the infinite loop of login
    # So we'll patch login to raise an exception or mock getpass to stop
    with patch("wealthgrabber.auth.getpass.getpass", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            get_authenticated_client(force_login=False)

    # Verify it tried to use the token but failed
    mock_ws_api.from_token.assert_called()


# Skipping test for full interactive login loop as it requires mocking multiple inputs and API calls
# efficiently which is brittle.


@patch("wealthgrabber.auth.keyring")
@patch("wealthgrabber.auth.WSAPISession")
@patch("wealthgrabber.auth.WealthsimpleAPI")
def test_get_authenticated_client_with_explicit_username(
    mock_ws_api, mock_session_cls, mock_keyring
):
    """Test authentication with explicitly provided username."""
    # Mock session exists for the explicit username
    mock_keyring.get_password.return_value = '{"valid": "json"}'

    mock_session = MagicMock()
    mock_session_cls.from_json.return_value = mock_session

    mock_ws = MagicMock()
    mock_ws_api.from_token.return_value = mock_ws

    # Run with explicit username
    client = get_authenticated_client(
        force_login=False, username="explicit@example.com"
    )

    # Verify - should NOT check for cached email, should use explicit username
    assert client == mock_ws
    # Should get session for explicit username
    mock_keyring.get_password.assert_called_with(
        "wealthsimple-account-viewer.explicit@example.com", "session"
    )


@patch("wealthgrabber.auth.keyring")
@patch("wealthgrabber.auth.WSAPISession")
@patch("wealthgrabber.auth.WealthsimpleAPI")
@patch("builtins.input")
def test_get_authenticated_client_no_cached_email(
    mock_input, mock_ws_api, mock_session_cls, mock_keyring
):
    """Test authentication when no cached email exists."""
    # No cached email, user provides email
    mock_input.return_value = "newuser@example.com"
    # First call (get cached email) returns None, second call gets session
    mock_keyring.get_password.side_effect = [None, '{"valid": "json"}']

    mock_session = MagicMock()
    mock_session_cls.from_json.return_value = mock_session

    mock_ws = MagicMock()
    mock_ws_api.from_token.return_value = mock_ws

    # Run
    client = get_authenticated_client(force_login=False)

    # Verify - should have prompted for email
    mock_input.assert_called_once()
    assert client == mock_ws


@patch("wealthgrabber.auth.keyring")
@patch("builtins.print")
def test_logout_with_cached_username(mock_print, mock_keyring):
    """Test logout with cached username."""
    mock_keyring.get_password.return_value = "testuser@example.com"

    logout()

    # Should get cached email
    mock_keyring.get_password.assert_called_with(
        "wealthsimple-account-viewer", "last_email"
    )
    # Should delete session
    mock_keyring.delete_password.assert_called_with(
        "wealthsimple-account-viewer.testuser@example.com", "session"
    )
    # Should print success message
    assert any("Cleared session" in str(call) for call in mock_print.call_args_list)


@patch("wealthgrabber.auth.keyring")
@patch("builtins.print")
def test_logout_with_explicit_username(mock_print, mock_keyring):
    """Test logout with explicitly provided username."""
    logout(username="specific@example.com")

    # Should NOT get cached email
    mock_keyring.get_password.assert_not_called()
    # Should delete session for specific user
    mock_keyring.delete_password.assert_called_with(
        "wealthsimple-account-viewer.specific@example.com", "session"
    )


@patch("wealthgrabber.auth.keyring")
@patch("builtins.print")
def test_logout_clear_email(mock_print, mock_keyring):
    """Test logout with clear_email flag."""
    mock_keyring.get_password.return_value = "testuser@example.com"

    logout(clear_email=True)

    # Should delete both session and cached email
    assert mock_keyring.delete_password.call_count == 2
    calls = [str(call) for call in mock_keyring.delete_password.call_args_list]
    assert any("session" in call for call in calls)
    assert any("last_email" in call for call in calls)


@patch("wealthgrabber.auth.keyring")
@patch("builtins.print")
def test_logout_no_cached_username(mock_print, mock_keyring):
    """Test logout when no cached username exists."""
    mock_keyring.get_password.return_value = None

    logout()

    # Should print message about no cached session
    assert any("No cached session" in str(call) for call in mock_print.call_args_list)
    # Should not try to delete anything
    mock_keyring.delete_password.assert_not_called()
