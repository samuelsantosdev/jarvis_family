"""
Registration window: collects name, email, and password,
then calls the API to create a new account.
"""
import tkinter as tk
from tkinter import messagebox

from client.services.api_client import APIClient, APIError

# ── Colour palette ────────────────────────────────────────────────────────────
BG = "#1e1e2e"
FG = "#cdd6f4"
ENTRY_BG = "#313244"
ACCENT = "#89b4fa"
BTN_BG = "#585b70"
BTN_FG = "#cdd6f4"
FONT = ("Helvetica", 11)
FONT_BOLD = ("Helvetica", 11, "bold")
FONT_TITLE = ("Helvetica", 18, "bold")


class RegisterWindow(tk.Toplevel):
    """Modal registration dialog."""

    def __init__(self, parent: tk.Tk, api_client: APIClient):
        super().__init__(parent)
        self._api = api_client

        self.title("Jarvis Family – Create Account")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()  # make modal

        self._build()
        self._center(parent)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self) -> None:
        pad = {"padx": 30, "pady": 8}

        # Title
        tk.Label(self, text="Create Account", font=FONT_TITLE, bg=BG, fg=ACCENT).pack(pady=(30, 20))

        # Name
        tk.Label(self, text="Full Name", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x", **pad)
        self._name_var = tk.StringVar()
        tk.Entry(self, textvariable=self._name_var, font=FONT, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, relief="flat").pack(fill="x", **pad)

        # Email
        tk.Label(self, text="Email", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x", **pad)
        self._email_var = tk.StringVar()
        tk.Entry(self, textvariable=self._email_var, font=FONT, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, relief="flat").pack(fill="x", **pad)

        # Password
        tk.Label(self, text="Password", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x", **pad)
        self._pass_var = tk.StringVar()
        tk.Entry(self, textvariable=self._pass_var, font=FONT, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, show="•", relief="flat").pack(fill="x", **pad)

        # Confirm Password
        tk.Label(self, text="Confirm Password", font=FONT, bg=BG, fg=FG, anchor="w").pack(fill="x", **pad)
        self._pass2_var = tk.StringVar()
        tk.Entry(self, textvariable=self._pass2_var, font=FONT, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, show="•", relief="flat").pack(fill="x", **pad)

        # Register button
        tk.Button(
            self, text="Register", font=FONT_BOLD, bg=ACCENT, fg=BG,
            relief="flat", cursor="hand2", command=self._on_register,
        ).pack(fill="x", padx=30, pady=(16, 8))

        # Cancel
        tk.Button(
            self, text="Cancel", font=FONT, bg=BTN_BG, fg=BTN_FG,
            relief="flat", cursor="hand2", command=self.destroy,
        ).pack(fill="x", padx=30, pady=(0, 24))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_register(self) -> None:
        name = self._name_var.get().strip()
        email = self._email_var.get().strip()
        password = self._pass_var.get()
        password2 = self._pass2_var.get()

        if not name:
            messagebox.showwarning("Validation", "Please enter your full name.", parent=self)
            return
        if not email:
            messagebox.showwarning("Validation", "Please enter your email address.", parent=self)
            return
        if not password:
            messagebox.showwarning("Validation", "Please enter a password.", parent=self)
            return
        if password != password2:
            messagebox.showwarning("Validation", "Passwords do not match.", parent=self)
            return
        if len(password) < 6:
            messagebox.showwarning("Validation", "Password must be at least 6 characters.", parent=self)
            return

        try:
            result = self._api.register(name=name, email=email, password=password)
            messagebox.showinfo(
                "Registration Successful",
                f"{result.get('message', 'Account created!')}\n\n"
                "Please check your inbox and click the confirmation link before logging in.",
                parent=self,
            )
            self.destroy()
        except APIError as exc:
            messagebox.showerror("Registration Failed", exc.detail, parent=self)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not connect to the server:\n{exc}", parent=self)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        pw = parent.winfo_x() + parent.winfo_width() // 2
        ph = parent.winfo_y() + parent.winfo_height() // 2
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")
