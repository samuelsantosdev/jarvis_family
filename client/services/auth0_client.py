"""
Auth0 OAuth2 helper for the desktop client.

Flow
----
1. Call ``get_authorization_url()`` to obtain the Auth0 URL and a random state.
2. Open the URL in the system browser.
3. Start ``start_callback_server()`` which listens on localhost for the redirect.
4. Auth0 redirects to http://localhost:<port>/callback?code=...&state=...
5. The server captures the code, calls the API's /auth/social/callback, and
   invokes the provided ``on_success`` callback with the token response dict.
"""
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable, Optional

from client.config import API_BASE_URL, AUTH0_CALLBACK_PORT
from client.services.api_client import APIClient, APIError

import httpx


class Auth0Client:
    """Coordinates the Auth0 browser-based login flow for a desktop app."""

    CALLBACK_PATH = "/callback"

    def __init__(self, api_client: Optional[APIClient] = None):
        self._api = api_client or APIClient()
        self._state: Optional[str] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def login(
        self,
        connection: Optional[str],
        on_success: Callable[[dict], None],
        on_error: Callable[[str], None],
    ) -> None:
        """
        Open the browser for Auth0 login and start the local callback server.
        ``connection`` examples: ``"google-oauth2"``, ``"apple"``.
        """
        try:
            auth_url = self._api.get_social_login_url(connection=connection)
        except APIError as exc:
            on_error(str(exc))
            return

        # Inject state parameter so we can validate the callback
        self._state = secrets.token_urlsafe(16)
        parsed = urllib.parse.urlparse(auth_url)
        qs = dict(urllib.parse.parse_qsl(parsed.query))
        qs["state"] = self._state
        auth_url_with_state = parsed._replace(query=urllib.parse.urlencode(qs)).geturl()

        webbrowser.open(auth_url_with_state)

        # Start a background thread that runs the callback HTTP server
        thread = threading.Thread(
            target=self._run_callback_server,
            args=(on_success, on_error),
            daemon=True,
        )
        thread.start()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_callback_server(
        self,
        on_success: Callable[[dict], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Run a one-shot local HTTP server that captures the OAuth callback."""
        state_expected = self._state
        api_base = self._api.base_url
        api_client = self._api

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path != Auth0Client.CALLBACK_PATH:
                    self._respond(404, "Not found")
                    return

                qs = dict(urllib.parse.parse_qsl(parsed.query))
                code = qs.get("code")
                state = qs.get("state")
                error = qs.get("error")

                if error:
                    self._respond(400, f"Auth0 error: {error}")
                    self.server._result = ("error", error)  # type: ignore[attr-defined]
                    return

                if state != state_expected:
                    self._respond(400, "State mismatch – possible CSRF attack.")
                    self.server._result = ("error", "State mismatch.")  # type: ignore[attr-defined]
                    return

                if not code:
                    self._respond(400, "Missing authorization code.")
                    self.server._result = ("error", "Missing code.")  # type: ignore[attr-defined]
                    return

                # Exchange code via the API backend
                try:
                    resp = httpx.get(
                        f"{api_base}/auth/social/callback",
                        params={"code": code, "state": state},
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        api_client.token = data["access_token"]
                        self._respond(200, "Login successful! You can close this tab.")
                        self.server._result = ("ok", data)  # type: ignore[attr-defined]
                    else:
                        detail = resp.json().get("detail", resp.text)
                        self._respond(400, detail)
                        self.server._result = ("error", detail)  # type: ignore[attr-defined]
                except Exception as exc:
                    self._respond(500, str(exc))
                    self.server._result = ("error", str(exc))  # type: ignore[attr-defined]

            def _respond(self, code: int, body: str) -> None:
                html = (
                    f"<html><body style='font-family:Arial;text-align:center;margin-top:60px'>"
                    f"<h2>{'✅' if code == 200 else '❌'} {body}</h2>"
                    f"<p>You can close this tab and return to Jarvis Family.</p></body></html>"
                )
                encoded = html.encode()
                self.send_response(code)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *args, **kwargs) -> None:
                pass  # silence request logging

        server = HTTPServer(("localhost", AUTH0_CALLBACK_PORT), _Handler)
        server._result = None  # type: ignore[attr-defined]
        server.handle_request()  # serve exactly one request then stop

        result = server._result  # type: ignore[attr-defined]
        if result is None:
            on_error("No response received from Auth0.")
        elif result[0] == "ok":
            on_success(result[1])
        else:
            on_error(result[1])
