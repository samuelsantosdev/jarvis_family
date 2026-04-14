"""
Jarvis Family – Tkinter client entry-point.

Usage
-----
    python -m client.main
or
    python client/main.py
"""
import sys
import os

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.views.login import LoginWindow


def main() -> None:
    def on_login(user: dict) -> None:
        print(f"Logged in as {user['name']} <{user['email']}>")

    app = LoginWindow(on_login_success=on_login)
    app.mainloop()


if __name__ == "__main__":
    main()
