"""
Personal Finance Tracker & AI Advisor
======================================
A full Tkinter desktop app with:
  - Dashboard (income, expenses, savings summary)
  - Transaction Manager (add/delete/filter)
  - Embedded Matplotlib charts (pie + bar + savings)
  - AI-powered advice via Google Gemini API (FREE)

Requirements:
    pip install matplotlib requests

Usage:
    python personal_finance_tracker.py

    On first launch a dialog will ask for your Google Gemini API key.
    Get your FREE key at: https://aistudio.google.com/app/apikey
    It is saved locally in config.json for all future runs.
    You can update it any time via  Settings → Set API Key.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import datetime
import threading
import requests

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ── FILE PATHS ────────────────────────────────────────────────────────────────
DATA_FILE   = "finance_data.json"
CONFIG_FILE = "config.json"

# ── COLOUR PALETTE ────────────────────────────────────────────────────────────
BG_DARK   = "#0F1117"
BG_CARD   = "#1A1D27"
BG_INPUT  = "#242736"
ACCENT    = "#6C63FF"
ACCENT2   = "#00D4AA"
DANGER    = "#FF4F6D"
WARNING   = "#FFB347"
TEXT_MAIN = "#E8E8F0"
TEXT_DIM  = "#7B7D8E"

FONT_H1   = ("Helvetica Neue", 22, "bold")
FONT_H2   = ("Helvetica Neue", 14, "bold")
FONT_BODY = ("Helvetica Neue", 11)


INCOME_CATEGORIES  = ["Salary", "Freelance", "Investment", "Gift", "Bonus", "Rental Income", "Other Income"]
EXPENSE_CATEGORIES = ["Food", "Rent", "Transport", "Shopping", "Entertainment",
                      "Health", "Education", "Utilities", "EMI", "Insurance", "Other"]
CATEGORIES = INCOME_CATEGORIES + EXPENSE_CATEGORIES


# ── CONFIG (API KEY) ──────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_api_key():
    return load_config().get("gemini_api_key", "")

def set_api_key(key):
    cfg = load_config()
    cfg["gemini_api_key"] = key
    save_config(cfg)

# ── DATA LAYER ────────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"transactions": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_transaction(data, tx_type, category, amount, note, date):
    data["transactions"].append({
        "id": datetime.datetime.now().timestamp(),
        "type": tx_type,
        "category": category,
        "amount": round(float(amount), 2),
        "note": note,
        "date": date
    })
    save_data(data)

def delete_transaction(data, tx_id):
    data["transactions"] = [t for t in data["transactions"] if t["id"] != tx_id]
    save_data(data)

def get_summary(data):
    income   = sum(t["amount"] for t in data["transactions"] if t["type"] == "Income")
    expenses = sum(t["amount"] for t in data["transactions"] if t["type"] == "Expense")
    return income, expenses, income - expenses

# ── AI ADVICE (Google Gemini - FREE) ─────────────────────────────────────────

def get_ai_advice(data, callback):
    income, expenses, savings = get_summary(data)
    cat_breakdown = {}
    for t in data["transactions"]:
        if t["type"] == "Expense":
            cat_breakdown[t["category"]] = cat_breakdown.get(t["category"], 0) + t["amount"]

    prompt = (
        "You are an expert personal finance advisor in India. Analyse the following "
        "financial data and give DETAILED, SPECIFIC, PERSONALISED advice.\n\n"
        "IMPORTANT INSTRUCTIONS:\n"
        "- Do NOT start with 'Dear Client' or any greeting\n"
        "- Do NOT use numbered prefixes before section headings (no '1.' '2.' etc.)\n"
        "- Use ### for section headings\n"
        "- Use bullet points (- ) for all lists\n"
        "- Use **bold** for important numbers and keywords\n"
        "- Keep each section concise — max 3-4 bullet points per section\n"
        "- Always include specific ₹ amounts\n\n"
        f"📊 FINANCIAL SUMMARY:\n"
        f"  Total Income:   ₹{income:,.2f}\n"
        f"  Total Expenses: ₹{expenses:,.2f}\n"
        f"  Net Savings:    ₹{savings:,.2f}\n"
        f"  Savings Rate:   {(savings/income*100) if income else 0:.1f}%\n\n"
        f"💸 EXPENSE BREAKDOWN:\n"
        + "\n".join(
            f"  {k}: ₹{v:,.2f}  ({v/expenses*100:.1f}% of expenses)"
            for k, v in cat_breakdown.items()
        )
        + f"\n\nProvide analysis in these exact sections:\n\n"
        "### 📈 OVERALL FINANCIAL HEALTH\n"
        "### 🚨 RED FLAGS\n"
        "### 💡 ACTION STEPS THIS MONTH\n"
        "### 💰 INVESTMENT PLAN\n"
        "### 🎯 3-MONTH GOAL\n"
    )

    api_key = get_api_key()

    def worker():
        try:
            if not api_key:
                callback(
                    "No API key configured.\n\n"
                    "Go to  \u2699 Settings \u2192 Set API Key  and paste your Google Gemini key.\n\n"
                    "Get your FREE key at:\nhttps://aistudio.google.com/app/apikey"
                )
                return

            # Try models in order until one works
            models_to_try = [
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.0-pro",
            ]

            last_error = ""
            for model_name in models_to_try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model_name}:generateContent?key={api_key}"
                )
                body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 8192, "temperature": 0.7}
                }
                resp = requests.post(url, json=body, timeout=30)

                if resp.ok:
                    result = resp.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    callback(f"[Model used: {model_name}]\n\n{text}")
                    return

                try:
                    err = resp.json()
                    msg = err.get("error", {}).get("message", str(err))
                except Exception:
                    msg = resp.text

                last_error = f"[{model_name}] Error {resp.status_code}: {msg}"

                # Don't try more models if it's an auth error (wrong key)
                if resp.status_code in (400, 401, 403):
                    break

            # All models failed
            callback(
                f"\u26a0\ufe0f  All Gemini models failed. Last error:\n\n{last_error}\n\n"
                "─────────────────────────────────\n"
                "Please try:\n"
                "1. Go to https://aistudio.google.com/app/apikey\n"
                "2. DELETE your current key\n"
                "3. Click 'Create API key in new project'\n"
                "4. Copy and paste the new key in Settings → Set API Key"
            )

        except Exception as e:
            callback(f"\u26a0\ufe0f  Could not fetch AI advice:\n\n{e}")

    threading.Thread(target=worker, daemon=True).start()

# ── WIDGETS ───────────────────────────────────────────────────────────────────

def styled_button(parent, text, command, bg=ACCENT, fg="white", font=FONT_BODY, **kw):
    return tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, font=font, relief="flat",
        cursor="hand2", activebackground=ACCENT2,
        activeforeground="white", padx=12, pady=6, **kw
    )

def make_card(parent, title, init="₹0.00", val_color=ACCENT2, width=200, height=100):
    f = tk.Frame(parent, bg=BG_CARD, width=width, height=height,
                 highlightbackground=ACCENT, highlightthickness=1)
    f.pack_propagate(False)
    tk.Label(f, text=title, font=("Helvetica Neue", 10),
             fg=TEXT_DIM, bg=BG_CARD).pack(pady=(12, 2))
    lbl = tk.Label(f, text=init, font=("Helvetica Neue", 18, "bold"),
                   fg=val_color, bg=BG_CARD)
    lbl.pack()
    return f, lbl

# ── API KEY DIALOG ────────────────────────────────────────────────────────────

class APIKeyDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Set Google Gemini API Key")
        self.configure(bg=BG_DARK)
        self.geometry("520x230")
        self.resizable(False, False)
        self.grab_set()
        self.result = None

        tk.Label(self, text="🔑  Enter your Google Gemini API Key",
                 font=FONT_H2, fg=ACCENT2, bg=BG_DARK).pack(pady=(22, 4))
        tk.Label(self,
                 text="Get your FREE key at: https://aistudio.google.com/app/apikey\n"
                      "Your key is saved in config.json (local only, never uploaded).",
                 font=("Helvetica Neue", 9), fg=TEXT_DIM, bg=BG_DARK).pack()

        self.key_var = tk.StringVar(value=get_api_key())
        self._entry = tk.Entry(self, textvariable=self.key_var, width=54,
                               bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                               font=FONT_BODY, relief="flat", show="*")
        self._entry.pack(padx=30, pady=14, ipady=6)

        show_var = tk.BooleanVar(value=False)
        def toggle():
            self._entry.config(show="" if show_var.get() else "*")
        tk.Checkbutton(self, text="Show key", variable=show_var, command=toggle,
                       bg=BG_DARK, fg=TEXT_DIM, selectcolor=BG_CARD,
                       activebackground=BG_DARK, font=("Helvetica Neue", 9)).pack()

        btn_row = tk.Frame(self, bg=BG_DARK)
        btn_row.pack(pady=8)
        styled_button(btn_row, "💾 Save", self._save).pack(side="left", padx=6)
        styled_button(btn_row, "Cancel", self.destroy,
                      bg=BG_INPUT, fg=TEXT_DIM).pack(side="left", padx=6)

        self._entry.focus_set()
        self.bind("<Return>", lambda e: self._save())

    def _save(self):
        key = self.key_var.get().strip()
        if not key:
            messagebox.showerror("Empty", "Please paste your API key.", parent=self)
            return
        set_api_key(key)
        self.result = key
        self.destroy()

# ── MAIN APP ──────────────────────────────────────────────────────────────────

class FinanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("💰 Personal Finance Tracker & AI Advisor")
        self.geometry("1100x740")
        self.configure(bg=BG_DARK)
        self.resizable(True, True)

        self.data = load_data()

        self._build_menubar()
        self._build_header()
        self._build_notebook()
        self._build_status_bar()

        # Prompt for API key on first launch
        if not get_api_key():
            self.after(500, self._first_launch_key_prompt)

        self.refresh_all()

    # ── MENU BAR ──────────────────────────────────────────────────────────────

    def _build_menubar(self):
        bar = tk.Menu(self, bg=BG_CARD, fg=TEXT_MAIN,
                      activebackground=ACCENT, activeforeground="white", relief="flat")
        self.config(menu=bar)
        settings = tk.Menu(bar, tearoff=0, bg=BG_CARD, fg=TEXT_MAIN,
                           activebackground=ACCENT, activeforeground="white")
        settings.add_command(label="🔑  Set API Key",       command=self._open_key_dialog)
        settings.add_separator()
        settings.add_command(label="🗑  Clear All Data",    command=self._clear_all_data)
        bar.add_cascade(label="  ⚙ Settings  ", menu=settings)

    def _first_launch_key_prompt(self):
        messagebox.showinfo(
            "Welcome!",
            "Welcome to Personal Finance Tracker!\n\n"
            "To enable AI-powered advice, please enter your Google Gemini API key.\n\n"
            "Get your FREE key at:\nhttps://aistudio.google.com/app/apikey\n\n"
            "(You can skip this and add it later via  ⚙ Settings → Set API Key)"
        )
        self._open_key_dialog()

    def _open_key_dialog(self):
        dlg = APIKeyDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.set_status("API key saved ✓")

    def _clear_all_data(self):
        if messagebox.askyesno("Confirm", "Delete ALL transactions permanently?"):
            self.data = {"transactions": []}
            save_data(self.data)
            self.refresh_all()
            self.set_status("All data cleared.")

    # ── HEADER ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_CARD, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💰 Personal Finance Tracker",
                 font=FONT_H1, fg=ACCENT2, bg=BG_CARD).pack(side="left", padx=20)
        tk.Label(hdr,
                 text=datetime.datetime.now().strftime("%A, %d %B %Y"),
                 font=FONT_BODY, fg=TEXT_DIM, bg=BG_CARD).pack(side="right", padx=20)

    # ── NOTEBOOK ──────────────────────────────────────────────────────────────

    def _build_notebook(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TNotebook",     background=BG_DARK, borderwidth=0)
        s.configure("TNotebook.Tab", background=BG_CARD, foreground=TEXT_DIM,
                    padding=[14, 8], font=FONT_BODY)
        s.map("TNotebook.Tab",
              background=[("selected", BG_DARK)],
              foreground=[("selected", ACCENT2)])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_dash = tk.Frame(nb, bg=BG_DARK)
        self.tab_tx   = tk.Frame(nb, bg=BG_DARK)
        self.tab_ch   = tk.Frame(nb, bg=BG_DARK)
        self.tab_ai   = tk.Frame(nb, bg=BG_DARK)

        nb.add(self.tab_dash, text="  📊 Dashboard  ")
        nb.add(self.tab_tx,   text="  💳 Transactions  ")
        nb.add(self.tab_ch,   text="  📈 Charts  ")
        nb.add(self.tab_ai,   text="  🤖 AI Advisor  ")

        self._build_dashboard()
        self._build_transactions()
        self._build_charts_tab()
        self._build_ai_tab()

    # ── STATUS BAR ────────────────────────────────────────────────────────────

    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="  Ready")
        tk.Label(self, textvariable=self.status_var,
                 font=("Courier New", 9), fg=TEXT_DIM, bg=BG_CARD,
                 anchor="w", padx=10).pack(fill="x", side="bottom")

    def set_status(self, msg):
        self.status_var.set(f"  {msg}")
        self.after(4000, lambda: self.status_var.set("  Ready"))

    # ── DASHBOARD ─────────────────────────────────────────────────────────────

    def _build_dashboard(self):
        p = self.tab_dash

        row = tk.Frame(p, bg=BG_DARK)
        row.pack(fill="x", padx=20, pady=20)

        self.card_income,  self.lbl_income  = make_card(row, "💵 Total Income",   "₹0.00", ACCENT2)
        self.card_expense, self.lbl_expense = make_card(row, "💸 Total Expenses",  "₹0.00", DANGER)
        self.card_savings, self.lbl_savings = make_card(row, "🏦 Net Savings",     "₹0.00", WARNING)
        self.card_count,   self.lbl_count   = make_card(row, "📋 Transactions",    "0",     ACCENT)

        for c in [self.card_income, self.card_expense, self.card_savings, self.card_count]:
            c.pack(side="left", padx=10)

        tk.Label(p, text="Recent Transactions", font=FONT_H2,
                 fg=TEXT_MAIN, bg=BG_DARK).pack(anchor="w", padx=24, pady=(8, 4))

        self.dash_tree = self._make_treeview(
            p, ("Date", "Type", "Category", "Amount", "Note"), height=14
        )

    def _update_dashboard(self):
        income, expenses, savings = get_summary(self.data)
        self.lbl_income.config(text=f"₹{income:,.2f}")
        self.lbl_expense.config(text=f"₹{expenses:,.2f}")
        self.lbl_savings.config(text=f"₹{savings:,.2f}",
                                fg=ACCENT2 if savings >= 0 else DANGER)
        self.lbl_count.config(text=str(len(self.data["transactions"])))

        for row in self.dash_tree.get_children():
            self.dash_tree.delete(row)
        recent = sorted(self.data["transactions"], key=lambda x: x["date"], reverse=True)[:20]
        for t in recent:
            self.dash_tree.insert("", "end",
                values=(t["date"], t["type"], t["category"],
                        f"₹{t['amount']:,.2f}", t["note"]),
                tags=(t["type"].lower(),))
        self.dash_tree.tag_configure("income",  foreground=ACCENT2)
        self.dash_tree.tag_configure("expense", foreground=DANGER)

    # ── TRANSACTIONS ──────────────────────────────────────────────────────────

    def _build_transactions(self):
        p = self.tab_tx

        # Form
        form = tk.Frame(p, bg=BG_CARD, padx=20, pady=16)
        form.pack(fill="x", padx=20, pady=16)

        tk.Label(form, text="➕  Add New Transaction", font=FONT_H2,
                 fg=ACCENT2, bg=BG_CARD).grid(row=0, column=0, columnspan=6,
                                               sticky="w", pady=(0, 10))

        for i, lbl in enumerate(["Type", "Category", "Amount (₹)",
                                  "Date (YYYY-MM-DD)", "Note"]):
            tk.Label(form, text=lbl, font=("Helvetica Neue", 9),
                     fg=TEXT_DIM, bg=BG_CARD).grid(row=1, column=i, sticky="w", padx=6)

        self.type_var = tk.StringVar(value="Expense")
        type_cb = ttk.Combobox(form, textvariable=self.type_var,
                     values=["Income", "Expense"],
                     width=10, state="readonly")
        type_cb.grid(row=2, column=0, padx=6, pady=4)

        self.cat_var = tk.StringVar(value="Food")
        self.cat_cb = ttk.Combobox(form, textvariable=self.cat_var,
                     values=EXPENSE_CATEGORIES,
                     width=14, state="readonly")
        self.cat_cb.grid(row=2, column=1, padx=6, pady=4)

        def on_type_change(event=None):
            if self.type_var.get() == "Income":
                self.cat_cb["values"] = INCOME_CATEGORIES
                self.cat_var.set("Salary")
            else:
                self.cat_cb["values"] = EXPENSE_CATEGORIES
                self.cat_var.set("Food")

        type_cb.bind("<<ComboboxSelected>>", on_type_change)

        self.amount_var = tk.StringVar()
        tk.Entry(form, textvariable=self.amount_var, width=14,
                 bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                 font=FONT_BODY, relief="flat").grid(row=2, column=2, padx=6, pady=4, ipady=4)

        self.date_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(form, textvariable=self.date_var, width=16,
                 bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                 font=FONT_BODY, relief="flat").grid(row=2, column=3, padx=6, pady=4, ipady=4)

        self.note_var = tk.StringVar()
        tk.Entry(form, textvariable=self.note_var, width=26,
                 bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                 font=FONT_BODY, relief="flat").grid(row=2, column=4, padx=6, pady=4, ipady=4)

        btns = tk.Frame(form, bg=BG_CARD)
        btns.grid(row=2, column=5, padx=10)
        styled_button(btns, "➕ Add",             self._add_tx,    bg=ACCENT).pack(side="left", padx=4)
        styled_button(btns, "🗑 Delete Selected", self._delete_tx, bg=DANGER).pack(side="left", padx=4)

        # Filters
        filt = tk.Frame(p, bg=BG_DARK)
        filt.pack(fill="x", padx=20, pady=(0, 4))

        tk.Label(filt, text="Filter by:", font=FONT_BODY,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side="left")

        self.filter_type = tk.StringVar(value="All")
        for val in ["All", "Income", "Expense"]:
            tk.Radiobutton(filt, text=val, variable=self.filter_type, value=val,
                           command=self._update_transactions,
                           bg=BG_DARK, fg=TEXT_MAIN, selectcolor=BG_CARD,
                           activebackground=BG_DARK, font=FONT_BODY).pack(side="left", padx=8)

        tk.Label(filt, text="Category:", font=FONT_BODY,
                 fg=TEXT_DIM, bg=BG_DARK).pack(side="left", padx=(20, 4))
        self.filter_cat = tk.StringVar(value="All")
        cf = ttk.Combobox(filt, textvariable=self.filter_cat,
                          values=["All"] + CATEGORIES, width=14, state="readonly")
        cf.bind("<<ComboboxSelected>>", lambda e: self._update_transactions())
        cf.pack(side="left")

        # Table
        self.tx_tree = self._make_treeview(
            p, ("Date", "Type", "Category", "Amount", "Note"), height=18
        )

    def _add_tx(self):
        try:
            amount = float(self.amount_var.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Amount", "Please enter a valid positive number.")
            return
        try:
            datetime.date.fromisoformat(self.date_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Date", "Date must be YYYY-MM-DD.")
            return

        note = self.note_var.get().strip() or "-"
        add_transaction(self.data, self.type_var.get(), self.cat_var.get(),
                        amount, note, self.date_var.get().strip())
        self.amount_var.set("")
        self.note_var.set("")
        self.date_var.set(datetime.date.today().isoformat())
        self.refresh_all()
        self.set_status(f"Added: {self.type_var.get()} — {self.cat_var.get()} — ₹{amount:,.2f}")

    def _delete_tx(self):
        sel = self.tx_tree.selection()
        if not sel:
            messagebox.showinfo("Nothing selected", "Select a row to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected transaction(s)?"):
            return
        for item in sel:
            tx_id = self.tx_tree.item(item)["tags"][0]
            delete_transaction(self.data, float(tx_id))
        self.refresh_all()
        self.set_status("Deleted.")

    def _update_transactions(self):
        for row in self.tx_tree.get_children():
            self.tx_tree.delete(row)
        ftype = self.filter_type.get()
        fcat  = self.filter_cat.get()
        for t in sorted(self.data["transactions"], key=lambda x: x["date"], reverse=True):
            if ftype != "All" and t["type"] != ftype:
                continue
            if fcat != "All" and t["category"] != fcat:
                continue
            self.tx_tree.insert("", "end",
                values=(t["date"], t["type"], t["category"],
                        f"₹{t['amount']:,.2f}", t["note"]),
                tags=(str(t["id"]), t["type"].lower()))
        self.tx_tree.tag_configure("income",  foreground=ACCENT2)
        self.tx_tree.tag_configure("expense", foreground=DANGER)

    # ── CHARTS ────────────────────────────────────────────────────────────────

    def _build_charts_tab(self):
        p = self.tab_ch
        row = tk.Frame(p, bg=BG_DARK)
        row.pack(fill="x", padx=20, pady=10)
        styled_button(row, "🔄 Refresh Charts", self._update_charts).pack(side="left")
        self.chart_frame = tk.Frame(p, bg=BG_DARK)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=4)

    def _update_charts(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        cat_totals = {}
        monthly    = {}
        for t in self.data["transactions"]:
            if t["type"] == "Expense":
                cat_totals[t["category"]] = cat_totals.get(t["category"], 0) + t["amount"]
            m = t["date"][:7]
            if m not in monthly:
                monthly[m] = {"Income": 0, "Expense": 0}
            monthly[m][t["type"]] += t["amount"]

        COLORS = ["#6C63FF","#00D4AA","#FF4F6D","#FFB347","#4ECDC4",
                  "#45B7D1","#96CEB4","#FFEAA7","#DDA0DD","#98D8C8",
                  "#F7DC6F","#BB8FCE","#76D7C4"]

        fig = Figure(figsize=(11, 5), facecolor=BG_DARK)
        fig.subplots_adjust(wspace=0.38, left=0.07, right=0.97, top=0.88, bottom=0.18)
        ax1, ax2, ax3 = fig.add_subplot(131), fig.add_subplot(132), fig.add_subplot(133)

        # Pie
        if cat_totals:
            labels = list(cat_totals.keys())
            sizes  = list(cat_totals.values())
            wedges, _, ats = ax1.pie(
                sizes, labels=None, autopct="%1.0f%%",
                colors=COLORS[:len(labels)], startangle=140,
                pctdistance=0.82,
                wedgeprops=dict(width=0.5, edgecolor=BG_DARK, linewidth=2)
            )
            for at in ats:
                at.set_color(TEXT_MAIN); at.set_fontsize(7)
            ax1.legend(wedges, labels, loc="lower center",
                       bbox_to_anchor=(0.5, -0.32), ncol=2, fontsize=7,
                       frameon=False, labelcolor=TEXT_DIM)
        else:
            ax1.text(0, 0, "No expense data yet", color=TEXT_DIM,
                     ha="center", va="center", fontsize=9)
        ax1.set_title("Expenses by Category", color=TEXT_MAIN, fontsize=10, pad=10)
        ax1.set_facecolor(BG_CARD)

        # Bar income vs expense
        if monthly:
            months = sorted(monthly.keys())[-6:]
            iv = [monthly[m]["Income"]  for m in months]
            ev = [monthly[m]["Expense"] for m in months]
            x  = range(len(months))
            ax2.bar([i - 0.2 for i in x], iv, 0.4, color=ACCENT2, label="Income")
            ax2.bar([i + 0.2 for i in x], ev, 0.4, color=DANGER,  label="Expense")
            ax2.set_xticks(list(x))
            ax2.set_xticklabels(months, rotation=35, ha="right", color=TEXT_DIM, fontsize=8)
            ax2.tick_params(colors=TEXT_DIM)
            ax2.legend(fontsize=8, frameon=False, labelcolor=TEXT_DIM)
            ax2.yaxis.grid(True, color="#2A2D3E", linewidth=0.6)
            ax2.set_axisbelow(True)
        else:
            ax2.text(0.5, 0.5, "No monthly data yet", color=TEXT_DIM,
                     ha="center", va="center", transform=ax2.transAxes, fontsize=9)
        ax2.set_title("Income vs Expenses by Month", color=TEXT_MAIN, fontsize=10, pad=10)
        ax2.set_facecolor(BG_CARD)
        ax2.spines[["top","right","left","bottom"]].set_visible(False)

        # Savings bar
        if monthly:
            months = sorted(monthly.keys())[-6:]
            sv     = [monthly[m]["Income"] - monthly[m]["Expense"] for m in months]
            ax3.bar(months, sv,
                    color=[ACCENT2 if v >= 0 else DANGER for v in sv],
                    edgecolor=BG_DARK, linewidth=1.5)
            ax3.axhline(0, color=TEXT_DIM, linewidth=0.8, linestyle="--")
            ax3.set_xticklabels(months, rotation=35, ha="right", color=TEXT_DIM, fontsize=8)
            ax3.tick_params(colors=TEXT_DIM)
            ax3.yaxis.grid(True, color="#2A2D3E", linewidth=0.6)
            ax3.set_axisbelow(True)
        else:
            ax3.text(0.5, 0.5, "No data yet", color=TEXT_DIM,
                     ha="center", va="center", transform=ax3.transAxes, fontsize=9)
        ax3.set_title("Monthly Net Savings", color=TEXT_MAIN, fontsize=10, pad=10)
        ax3.set_facecolor(BG_CARD)
        ax3.spines[["top","right","left","bottom"]].set_visible(False)

        FigureCanvasTkAgg(fig, master=self.chart_frame).get_tk_widget().pack(
            fill="both", expand=True
        )
        # draw after packing
        FigureCanvasTkAgg(fig, master=self.chart_frame).draw()

    # ── AI ADVISOR ────────────────────────────────────────────────────────────

    def _build_ai_tab(self):
        p = self.tab_ai

        top = tk.Frame(p, bg=BG_DARK)
        top.pack(fill="x", padx=20, pady=16)
        tk.Label(top, text="🤖  AI Financial Advisor",
                 font=FONT_H1, fg=ACCENT2, bg=BG_DARK).pack(side="left")
        styled_button(top, "✨ Get AI Advice", self._fetch_ai_advice,
                      bg=ACCENT, font=FONT_H2).pack(side="right")

        self.ai_summary_lbl = tk.Label(p, text="", font=FONT_BODY,
                                       fg=TEXT_DIM, bg=BG_DARK, justify="left")
        self.ai_summary_lbl.pack(anchor="w", padx=22, pady=(0, 8))

        box = tk.Frame(p, bg=BG_CARD,
                       highlightbackground=ACCENT, highlightthickness=1)
        box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.ai_text = tk.Text(
            box, wrap="word",
            bg=BG_CARD, fg=TEXT_MAIN, font=("Helvetica Neue", 11),
            insertbackground=TEXT_MAIN, relief="flat",
            padx=18, pady=18, state="disabled"
        )
        sb = ttk.Scrollbar(box, orient="vertical", command=self.ai_text.yview)
        self.ai_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.ai_text.pack(fill="both", expand=True)

        self._set_ai_text(
            "Welcome to your AI Financial Advisor! 👋\n\n"
            "Powered by Google Gemini (FREE)\n\n"
            "Steps to get started:\n"
            "  1. Get your FREE Gemini API key at:\n"
            "     https://aistudio.google.com/app/apikey\n\n"
            "  2. Go to  ⚙ Settings → Set API Key  and paste it.\n\n"
            "  3. Add transactions in the  💳 Transactions  tab.\n\n"
            "  4. Come back here and click  ✨ Get AI Advice.\n\n"
            "Gemini will analyse your income, expenses, and spending patterns\n"
            "and give you 5 personalised, actionable financial tips — completely free!"
        )

    def _update_ai_summary(self):
        income, expenses, savings = get_summary(self.data)
        if income == 0 and expenses == 0:
            self.ai_summary_lbl.config(
                text="  No transactions yet — add some to see your summary here.",
                fg=TEXT_DIM
            )
            return
        ratio = (expenses / income * 100) if income else 0
        color = DANGER if ratio > 80 else WARNING if ratio > 60 else ACCENT2
        self.ai_summary_lbl.config(
            text=(f"  Income: ₹{income:,.2f}   |   Expenses: ₹{expenses:,.2f}   |   "
                  f"Savings: ₹{savings:,.2f}   |   Expense ratio: {ratio:.1f}%"),
            fg=color
        )

    def _set_ai_text(self, text):
        """Plain text setter used for welcome/error messages."""
        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("end", text)
        self.ai_text.config(state="disabled")

    def _render_ai_markdown(self, text):
        """Render markdown-like text with proper formatting in the Text widget."""
        import re

        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", "end")

        # Define text tags
        self.ai_text.tag_configure("heading",
            font=("Helvetica Neue", 13, "bold"), foreground=ACCENT2,
            spacing1=14, spacing3=6)
        self.ai_text.tag_configure("bold",
            font=("Helvetica Neue", 11, "bold"), foreground=TEXT_MAIN)
        self.ai_text.tag_configure("normal",
            font=("Helvetica Neue", 11), foreground=TEXT_MAIN, spacing1=2)
        self.ai_text.tag_configure("dim",
            font=("Helvetica Neue", 10), foreground=TEXT_DIM)
        self.ai_text.tag_configure("divider",
            font=("Helvetica Neue", 8), foreground=TEXT_DIM, spacing1=6, spacing3=6)

        # Clean up the text
        text = re.sub(r"\[Model used:.*?\]\n?", "", text).strip()

        # Remove "Dear Client," greeting lines at top
        text = re.sub(r"^Dear\s+\w+[,.]?\s*\n?", "", text, flags=re.IGNORECASE).strip()

        lines = text.split("\n")
        for line in lines:
            stripped = line.strip()

            # Skip raw dividers
            if re.match(r"^[-_*]{3,}$", stripped):
                self.ai_text.insert("end", "  " + "─" * 60 + "\n", "divider")
                continue

            # ### or ## Heading — strip ### and any leading numbers like "1." "2."
            if stripped.startswith("#"):
                heading_text = re.sub(r"^#+\s*", "", stripped)
                heading_text = re.sub(r"^\d+[\.\)]\s*", "", heading_text)
                heading_text = heading_text.replace("**", "").strip()
                self.ai_text.insert("end", "\n" + heading_text + "\n", "heading")
                continue

            # Bullet points: *, -, •
            if re.match(r"^[\*\-•]\s+", stripped):
                content = re.sub(r"^[\*\-•]\s+", "", stripped)
                self.ai_text.insert("end", "  ● ", "bold")
                self._insert_inline_bold(content)
                self.ai_text.insert("end", "\n", "normal")
                continue

            # Numbered list lines like "1. text" → bullet
            if re.match(r"^\d+[\.\)]\s+", stripped):
                content = re.sub(r"^\d+[\.\)]\s+", "", stripped)
                self.ai_text.insert("end", "  ● ", "bold")
                self._insert_inline_bold(content)
                self.ai_text.insert("end", "\n", "normal")
                continue

            # Empty line
            if stripped == "":
                self.ai_text.insert("end", "\n", "normal")
                continue

            # Normal paragraph line
            self._insert_inline_bold(stripped)
            self.ai_text.insert("end", "\n", "normal")

        self.ai_text.config(state="disabled")

    def _insert_inline_bold(self, text):
        """Insert a line of text, rendering **bold** parts."""
        import re
        parts = re.split(r"(\*\*.*?\*\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self.ai_text.insert("end", part[2:-2],
                    ("bold",))
            else:
                self.ai_text.insert("end", part, "normal")

    def _fetch_ai_advice(self):
        if not self.data["transactions"]:
            messagebox.showinfo("No data", "Add some transactions first.")
            return
        if not get_api_key():
            if messagebox.askyesno("API Key Missing",
                                   "No Gemini API key set.\n\nOpen Settings to add one now?"):
                self._open_key_dialog()
            return
        self._set_ai_text("⏳  Contacting Gemini AI — please wait a moment...")
        self.set_status("Fetching AI advice...")
        get_ai_advice(self.data, lambda txt: self.after(0, self._on_ai_response, txt))

    def _on_ai_response(self, text):
        # If it's an error message, show plain; otherwise render markdown
        if text.startswith("⚠️") or text.startswith("\u26a0"):
            self._set_ai_text(text)
        else:
            self._render_ai_markdown(text)
        self.set_status("AI advice received ✓")

    # ── TREEVIEW HELPER ───────────────────────────────────────────────────────

    def _make_treeview(self, parent, columns, height=12):
        s = ttk.Style()
        s.configure("Finance.Treeview",
                    background=BG_CARD, fieldbackground=BG_CARD,
                    foreground=TEXT_MAIN, rowheight=26,
                    borderwidth=0, font=FONT_BODY)
        s.configure("Finance.Treeview.Heading",
                    background=BG_INPUT, foreground=ACCENT2,
                    font=("Helvetica Neue", 10, "bold"), relief="flat")
        s.map("Finance.Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])

        frame = tk.Frame(parent, bg=BG_DARK)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        tv = ttk.Treeview(frame, columns=columns, show="headings",
                          height=height, style="Finance.Treeview",
                          selectmode="extended")
        widths = {"Date": 100, "Type": 80, "Category": 120,
                  "Amount": 110, "Note": 290}
        for col in columns:
            tv.heading(col, text=col)
            tv.column(col, width=widths.get(col, 120), anchor="center")

        sb = ttk.Scrollbar(frame, orient="vertical", command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        return tv

    # ── REFRESH ───────────────────────────────────────────────────────────────

    def refresh_all(self):
        self._update_dashboard()
        self._update_transactions()
        self._update_charts()
        self._update_ai_summary()


if __name__ == "__main__":
    app = FinanceApp()
    app.mainloop()
