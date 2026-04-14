"""
Login window: email/password login plus social login buttons (Gmail, Apple).
"""
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from client.services.api_client import APIClient, APIError
from client.services.auth0_client import Auth0Client
from client.views.register import RegisterWindow

# ── Colour palette ────────────────────────────────────────────────────────────
BG = "#1e1e2e"
FG = "#cdd6f4"
ENTRY_BG = "#313244"
ACCENT = "#89b4fa"
BTN_BG = "#585b70"
BTN_FG = "#cdd6f4"
GOOGLE_BG = "#ea4335"
APPLE_BG = "#000000"
APPLE_FG = "#ffffff"
FONT = ("Helvetica", 11)
FONT_BOLD = ("Helvetica", 11, "bold")
FONT_TITLE = ("Helvetica", 20, "bold")
FONT_SMALL = ("Helvetica", 9)


class LoginWindow(tk.Tk):
    """
    Main application window.
    Shown first; opens RegisterWindow on demand.
    After a successful login, calls ``on_login_success`` with the user dict.
    """

    def __init__(self, on_login_success: Optional[Callable[[dict], None]] = None):
        super().__init__()
        self._api = APIClient()
        self._auth0 = Auth0Client(api_client=self._api)
        self._on_login_success = on_login_success

        self.title("Jarvis Family – Login")
        self.resizable(False, False)
        self.configure(bg=BG)

        self._build()
        self._center()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        # ─── Header ───
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", pady=(30, 0))
        tk.Label(header, text="🤖", font=("Helvetica", 36), bg=BG, fg=ACCENT).pack()
        tk.Label(header, text="Jarvis Family", font=FONT_TITLE, bg=BG, fg=ACCENT).pack()
        tk.Label(header, text="Sign in to your account", font=FONT_SMALL, bg=BG, fg=BTN_FG).pack(pady=(4, 0))

        # ─── Social login buttons ───
        social_frame = tk.Frame(self, bg=BG)
        social_frame.pack(fill="x", padx=30, pady=(24, 0))

        tk.Button(
            social_frame, text="🔴  Continue with Gmail", font=FONT_BOLD,
            bg=GOOGLE_BG, fg="#ffffff", relief="flat", cursor="hand2",
            command=lambda: self._social_login("google-oauth2"),
        ).pack(fill="x", pady=4)

        tk.Button(
            social_frame, text="🍎  Continue with Apple", font=FONT_BOLD,
            bg=APPLE_BG, fg=APPLE_FG, relief="flat", cursor="hand2",
            command=lambda: self._social_login("apple"),
        ).pack(fill="x", pady=4)

        tk.Button(
            social_frame, text="✉️  Continue with Email (SSO)", font=FONT_BOLD,
            bg=BTN_BG, fg=BTN_FG, relief="flat", cursor="hand2",
            command=lambda: self._social_login(None),
        ).pack(fill="x", pady=4)

        # ─── Divider ───
        div = tk.Frame(self, bg=BG)
        div.pack(fill="x", padx=30, pady=(16, 0))
        tk.Frame(div, bg=BTN_BG, height=1).pack(fill="x", side="left", expand=True, pady=8)
        tk.Label(div, text=" or ", font=FONT_SMALL, bg=BG, fg=BTN_FG).pack(side="left")
        tk.Frame(div, bg=BTN_BG, height=1).pack(fill="x", side="left", expand=True, pady=8)

        # ─── Email / password form ───
        form = tk.Frame(self, bg=BG)
        form.pack(fill="x", padx=30)

        tk.Label(form, text="Email", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x")
        self._email_var = tk.StringVar()
        tk.Entry(form, textvariable=self._email_var, font=FONT, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, relief="flat").pack(fill="x", pady=(2, 10))

        tk.Label(form, text="Password", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x")
        self._pass_var = tk.StringVar()
        self._pass_entry = tk.Entry(
            form, textvariable=self._pass_var, font=FONT, bg=ENTRY_BG, fg=FG,
            insertbackground=FG, show="•", relief="flat",
        )
        self._pass_entry.pack(fill="x", pady=(2, 0))
        self._pass_entry.bind("<Return>", lambda _e: self._on_login())

        # Show / hide password
        self._show_pass = tk.BooleanVar(value=False)
        tk.Checkbutton(
            form, text="Show password", variable=self._show_pass,
            font=FONT_SMALL, bg=BG, fg=BTN_FG, selectcolor=BG,
            activebackground=BG, activeforeground=BTN_FG,
            command=self._toggle_pass,
        ).pack(anchor="w", pady=(4, 0))

        # ─── Login button ───
        tk.Button(
            self, text="Login", font=FONT_BOLD, bg=ACCENT, fg=BG,
            relief="flat", cursor="hand2", command=self._on_login,
        ).pack(fill="x", padx=30, pady=(16, 8))

        # ─── Register link ───
        reg_frame = tk.Frame(self, bg=BG)
        reg_frame.pack(pady=(0, 24))
        tk.Label(reg_frame, text="Don't have an account? ", font=FONT_SMALL, bg=BG, fg=BTN_FG).pack(side="left")
        lnk = tk.Label(reg_frame, text="Register", font=FONT_SMALL, bg=BG, fg=ACCENT, cursor="hand2")
        lnk.pack(side="left")
        lnk.bind("<Button-1>", lambda _e: self._open_register())

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_login(self) -> None:
        email = self._email_var.get().strip()
        password = self._pass_var.get()

        if not email or not password:
            messagebox.showwarning("Validation", "Please enter your email and password.", parent=self)
            return

        try:
            user = self._api.login(email=email, password=password)
            self._handle_login_success(user)
        except APIError as exc:
            messagebox.showerror("Login Failed", exc.detail, parent=self)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not connect to the server:\n{exc}", parent=self)

    def _social_login(self, connection: Optional[str]) -> None:
        try:
            self._auth0.login(
                connection=connection,
                on_success=lambda user: self.after(0, self._handle_login_success, user),
                on_error=lambda msg: self.after(
                    0, messagebox.showerror, "Social Login Failed", msg
                ),
            )
            messagebox.showinfo(
                "Browser Opening",
                "A browser window has been opened for authentication.\n"
                "Complete the login there and return to this window.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self)

    def _handle_login_success(self, user: dict) -> None:
        if self._on_login_success:
            self._on_login_success(user)
        else:
            messagebox.showinfo(
                "Login Successful",
                f"Welcome, {user.get('name', user.get('email'))}! 🎉",
                parent=self,
            )

    def _open_register(self) -> None:
        RegisterWindow(self, self._api)

    def _toggle_pass(self) -> None:
        self._pass_entry.config(show="" if self._show_pass.get() else "•")

    # ── Layout ────────────────────────────────────────────────────────────────

    def _center(self) -> None:
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
