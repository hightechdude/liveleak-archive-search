#!/usr/bin/env python3
"""
LiveLeak Archive Search - GUI Version
Version 1.0.0
Created by HIGHTECHDUDE
"""

import csv
import re
import threading
import time
import queue
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Union

import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox
import tkinter as tk

import cdx_toolkit

try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False

# ====================== APP INFO ======================
APP_NAME = "LiveLeak Archive Search"
APP_VERSION = "1.0.0"
APP_AUTHOR = "HIGHTECHDUDE"
# ======================================================


# --------------------------------------------------
# Boolean Expression Tree
# --------------------------------------------------
@dataclass
class Term:
    value: str
    phrase: bool = False

@dataclass
class Not:
    expr: "Expr"

@dataclass
class And:
    left: "Expr"
    right: "Expr"

@dataclass
class Or:
    left: "Expr"
    right: "Expr"

Expr = Union[Term, Not, And, Or]


class BooleanParser:
    def __init__(self, query: str):
        self.tokens = self._tokenize(query)
        self.pos = 0

    def _tokenize(self, query: str) -> List[str]:
        phrases = {}
        def repl(m):
            key = f"__PHRASE{len(phrases)}__"
            phrases[key] = m.group(1)
            return key
        q = re.sub(r'"([^"]*)"', repl, query)
        raw = re.split(r"(\bAND\b|\bOR\b|\bNOT\b|\(|\))", q, flags=re.IGNORECASE)
        tokens = []
        for t in raw:
            t = t.strip()
            if t:
                tokens.append(phrases.get(t, t) if t.startswith("__PHRASE") else t)
        return tokens

    def parse(self) -> Expr:
        expr = self._parse_or()
        if self.pos < len(self.tokens):
            raise ValueError(f"Unexpected token: {self.tokens[self.pos]}")
        return expr

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _consume(self, expected=None):
        tok = self._peek()
        if tok is None:
            raise ValueError("Unexpected end of query")
        if expected and tok.upper() != expected.upper():
            raise ValueError(f"Expected {expected}, got {tok}")
        self.pos += 1
        return tok

    def _parse_or(self):
        left = self._parse_and()
        while self._peek() and self._peek().upper() == "OR":
            self._consume("OR")
            left = Or(left, self._parse_and())
        return left

    def _parse_and(self):
        left = self._parse_not()
        while self._peek() and self._peek().upper() == "AND":
            self._consume("AND")
            left = And(left, self._parse_not())
        return left

    def _parse_not(self):
        if self._peek() and self._peek().upper() == "NOT":
            self._consume("NOT")
            return Not(self._parse_not())
        return self._parse_primary()

    def _parse_primary(self):
        tok = self._peek()
        if tok == "(":
            self._consume("(")
            expr = self._parse_or()
            self._consume(")")
            return expr
        if tok is None:
            raise ValueError("Unexpected end of query")
        self._consume()
        return Term(tok, phrase=" " in tok)


def eval_expr(expr: Expr, text: str) -> bool:
    text_lower = text.lower()
    if isinstance(expr, Term):
        needle = expr.value.lower()
        if expr.phrase:
            return needle in text_lower
        return re.search(rf"\b{re.escape(needle)}\b", text_lower) is not None
    if isinstance(expr, Not):
        return not eval_expr(expr.expr, text)
    if isinstance(expr, And):
        return eval_expr(expr.left, text) and eval_expr(expr.right, text)
    if isinstance(expr, Or):
        return eval_expr(expr.left, text) or eval_expr(expr.right, text)
    return False


def extract_full_paragraph(text: str, expr: Expr, max_chars: int = 500) -> str:
    paragraphs = re.split(r"\n\s*\n", text)
    best = ""
    for p in paragraphs:
        p = p.strip()
        if p and eval_expr(expr, p) and len(p) > len(best):
            best = p
    if best:
        return best[:max_chars].strip()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if eval_expr(expr, line):
            start = max(0, i - 1)
            end = min(len(lines), i + 3)
            return " ".join(l.strip() for l in lines[start:end] if l.strip())[:max_chars]
    return ""


# --------------------------------------------------
# About Dialog
# --------------------------------------------------
class AboutDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About")
        self.geometry("420x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center the window
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 210
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 140
        self.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(self)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text=APP_NAME,
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 4))

        ctk.CTkLabel(frame, text=f"Version {APP_VERSION}",
                     font=ctk.CTkFont(size=13)).pack(pady=2)

        ctk.CTkLabel(frame, text="─" * 32).pack(pady=8)

        ctk.CTkLabel(frame, text="Created by",
                     font=ctk.CTkFont(size=12)).pack()
        ctk.CTkLabel(frame, text=APP_AUTHOR,
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="#4fc3f7").pack(pady=(0, 12))

        ctk.CTkLabel(frame,
                     text="Search archived LiveLeak pages\nusing Wayback Machine & Common Crawl",
                     font=ctk.CTkFont(size=11),
                     justify="center").pack(pady=4)

        ctk.CTkButton(frame, text="Close", width=100, command=self.destroy).pack(pady=15)


# --------------------------------------------------
# Main Application
# --------------------------------------------------
class LiveLeakSearchApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1100x820")
        self.minsize(950, 700)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.search_thread = None
        self.stop_flag = False
        self.log_queue = queue.Queue()
        self.results_data = []

        self.create_widgets()
        self.after(100, self.process_log_queue)

        # Try to set window icon
        try:
            self.iconbitmap("icon.ico")
        except Exception:
            pass

    def create_widgets(self):
        # ===== Query =====
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(top, text="Boolean Query", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(6, 0))
        self.query_entry = ctk.CTkEntry(top, height=34,
            placeholder_text='Michigan AND (accident OR crash)   |   "dashcam crash" AND Michigan NOT motorcycle')
        self.query_entry.pack(fill="x", padx=10, pady=6)
        self.query_entry.insert(0, "Michigan AND (accident OR crash)")

        # ===== Options =====
        opts = ctk.CTkFrame(self)
        opts.pack(fill="x", padx=12, pady=6)

        df = ctk.CTkFrame(opts, fg_color="transparent")
        df.pack(side="left", padx=8, pady=6)
        ctk.CTkLabel(df, text="From:").pack(side="left")
        self.from_year = ctk.CTkEntry(df, width=65)
        self.from_year.insert(0, "2008")
        self.from_year.pack(side="left", padx=3)
        ctk.CTkLabel(df, text="To:").pack(side="left", padx=(8, 0))
        self.to_year = ctk.CTkEntry(df, width=65)
        self.to_year.insert(0, "2021")
        self.to_year.pack(side="left", padx=3)

        sf = ctk.CTkFrame(opts, fg_color="transparent")
        sf.pack(side="left", padx=15, pady=6)
        self.var_wayback = ctk.BooleanVar(value=True)
        self.var_cc = ctk.BooleanVar(value=True)
        self.var_images = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sf, text="Wayback", variable=self.var_wayback, width=80).pack(side="left", padx=4)
        ctk.CTkCheckBox(sf, text="Common Crawl", variable=self.var_cc, width=110).pack(side="left", padx=4)
        ctk.CTkCheckBox(sf, text="Images", variable=self.var_images, width=70).pack(side="left", padx=4)

        mf = ctk.CTkFrame(opts, fg_color="transparent")
        mf.pack(side="left", padx=10, pady=6)
        ctk.CTkLabel(mf, text="Delay:").pack(side="left")
        self.delay_entry = ctk.CTkEntry(mf, width=45)
        self.delay_entry.insert(0, "1.0")
        self.delay_entry.pack(side="left", padx=3)
        self.var_dryrun = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(mf, text="Dry Run", variable=self.var_dryrun, width=80).pack(side="left", padx=8)

        # ===== Output + ES =====
        out = ctk.CTkFrame(self)
        out.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(out, text="CSV:").pack(side="left", padx=(8, 3))
        self.output_entry = ctk.CTkEntry(out, width=400)
        self.output_entry.insert(0, str(Path.cwd() / "liveleak_search_hits.csv"))
        self.output_entry.pack(side="left", padx=3)
        ctk.CTkButton(out, text="Browse", width=70, command=self.browse_output).pack(side="left", padx=4)

        self.var_es = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(out, text="Elasticsearch", variable=self.var_es).pack(side="left", padx=12)

        # ===== Buttons =====
        btn = ctk.CTkFrame(self, fg_color="transparent")
        btn.pack(fill="x", padx=12, pady=8)

        self.start_btn = ctk.CTkButton(btn, text="▶  Start Search", width=130, height=34,
                                       fg_color="#2e7d32", hover_color="#1b5e20", command=self.start_search)
        self.start_btn.pack(side="left", padx=4)

        self.stop_btn = ctk.CTkButton(btn, text="⏹  Stop", width=90, height=34,
                                      fg_color="#c62828", hover_color="#b71c1c",
                                      state="disabled", command=self.stop_search)
        self.stop_btn.pack(side="left", padx=4)

        ctk.CTkButton(btn, text="Open Folder", width=100, height=34, command=self.open_folder).pack(side="left", padx=4)
        ctk.CTkButton(btn, text="Clear Results", width=100, height=34, command=self.clear_results).pack(side="left", padx=4)

        # About button on the right
        ctk.CTkButton(btn, text="About", width=80, height=34,
                      fg_color="#455a64", hover_color="#37474f",
                      command=self.show_about).pack(side="right", padx=4)

        # ===== Progress =====
        prog = ctk.CTkFrame(self)
        prog.pack(fill="x", padx=12, pady=4)
        self.progress = ctk.CTkProgressBar(prog)
        self.progress.pack(fill="x", padx=8, pady=(6, 2))
        self.progress.set(0)
        self.status_label = ctk.CTkLabel(prog, text="Ready", anchor="w")
        self.status_label.pack(fill="x", padx=8, pady=(0, 6))

        # ===== Results Table =====
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        ctk.CTkLabel(table_frame, text="Results", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(6, 2))

        tree_container = ctk.CTkFrame(table_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white",
                        fieldbackground="#2b2b2b", rowheight=26, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#1f538d", foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#1f538d")])

        columns = ("source", "year", "date", "url", "snippet")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("source", text="Source")
        self.tree.heading("year", text="Year")
        self.tree.heading("date", text="Date")
        self.tree.heading("url", text="Original URL")
        self.tree.heading("snippet", text="Matching Paragraph")

        self.tree.column("source", width=90, anchor="center")
        self.tree.column("year", width=55, anchor="center")
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("url", width=280)
        self.tree.column("snippet", width=420)

        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)

        # ===== Log =====
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkLabel(log_frame, text="Log", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self.log_text = ctk.CTkTextbox(log_frame, height=90, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_text.pack(fill="x", padx=8, pady=6)

    def show_about(self):
        AboutDialog(self)

    # ---------- Helpers ----------
    def log(self, msg: str):
        self.log_queue.put(msg)

    def process_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        self.after(120, self.process_log_queue)

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def open_folder(self):
        path = Path(self.output_entry.get()).parent
        import subprocess, sys
        if sys.platform == "win32":
            subprocess.Popen(f'explorer "{path}"')
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def clear_results(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data.clear()

    def add_result_row(self, source, year, date, url, snippet, archive_url):
        self.results_data.append(archive_url)
        self.tree.insert("", "end", values=(source, year, date, url[:80], snippet[:120]))

    def on_double_click(self, event):
        item = self.tree.selection()
        if not item:
            return
        idx = self.tree.index(item[0])
        if 0 <= idx < len(self.results_data):
            import webbrowser
            webbrowser.open(self.results_data[idx])

    def set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.start_btn.configure(state=state)
        self.stop_btn.configure(state="normal" if running else "disabled")

    # ---------- Search ----------
    def start_search(self):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showwarning("Missing Query", "Please enter a search query.")
            return
        try:
            tree = BooleanParser(query).parse()
        except ValueError as e:
            messagebox.showerror("Query Error", str(e))
            return

        try:
            from_year = int(self.from_year.get())
            to_year = int(self.to_year.get())
            delay = float(self.delay_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Years and Delay must be numbers.")
            return

        if from_year > to_year:
            from_year, to_year = to_year, from_year

        sources = []
        if self.var_wayback.get():
            sources.append(("wayback", 180))
        if self.var_cc.get():
            sources.append(("commoncrawl", 100))
        if self.var_images.get():
            sources.append(("images", 60))

        if not sources:
            messagebox.showwarning("No Sources", "Select at least one source.")
            return

        self.stop_flag = False
        self.set_running(True)
        self.progress.set(0)
        self.clear_results()
        self.log_text.delete("1.0", "end")
        self.log(f"Query : {query}")
        self.log(f"Years : {from_year} → {to_year}")
        self.log("-" * 55)

        self.search_thread = threading.Thread(
            target=self.run_search,
            args=(tree, from_year, to_year, sources, delay,
                  self.output_entry.get(), self.var_dryrun.get(), self.var_es.get()),
            daemon=True
        )
        self.search_thread.start()

    def stop_search(self):
        self.stop_flag = True
        self.log("Stopping...")

    def run_search(self, tree, from_year, to_year, sources, delay, output_path, dry_run, use_es):
        years = list(range(from_year, to_year + 1))
        tasks = [(s, y, lim) for y in years for s, lim in sources]
        total = len(tasks)
        done = 0
        total_hits = 0

        csv_path = Path(output_path)
        mode = "a" if csv_path.exists() and not dry_run else "w"
        fieldnames = ["source", "year", "timestamp", "date", "original_url", "archive_url", "matching_paragraph"]

        try:
            with open(csv_path, mode, newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
                if mode == "w":
                    writer.writeheader()

                for source, year, limit in tasks:
                    if self.stop_flag:
                        self.log("Stopped by user.")
                        break
                    self.status_label.configure(text=f"Searching {source} • {year}")
                    hits = self.search_one(source, year, limit, writer, tree, delay, dry_run)
                    total_hits += hits
                    done += 1
                    self.progress.set(done / total)

            self.log("-" * 55)
            self.log(f"Finished. Total hits: {total_hits}")
            self.log(f"Saved to: {csv_path}")
            self.status_label.configure(text=f"Done — {total_hits} hits")
        except Exception as e:
            self.log(f"[ERROR] {e}")
            self.status_label.configure(text="Error")
        finally:
            self.set_running(False)

    def search_one(self, source, year, limit, writer, tree, delay, dry_run):
        if dry_run:
            self.log(f"[DRY-RUN] {source} {year}")
            return 0

        self.log(f"→ {source.upper()} {year}")

        if source == "wayback":
            cdx = cdx_toolkit.CDXFetcher(source="ia")
            url_pattern, match_type = "liveleak.com", "domain"
            filters = ["status:200", "mime:text/html"]
        elif source == "commoncrawl":
            cdx = cdx_toolkit.CDXFetcher(source="cc")
            url_pattern, match_type = "liveleak.com/*", "prefix"
            filters = ["=status:200", "mime:text/html"]
        else:
            cdx = cdx_toolkit.CDXFetcher(source="ia")
            url_pattern, match_type = "liveleak.com", "domain"
            filters = ["status:200", "mime:image/.*"]

        hits = 0
        try:
            iterator = cdx.iter(url_pattern, match_type=match_type,
                                from_ts=str(year), to=str(year),
                                limit=limit, filter=filters,
                                collapse="digest" if source in ("wayback", "images") else None)
        except Exception as e:
            self.log(f"  [!] {e}")
            return 0

        for obj in iterator:
            if self.stop_flag:
                break

            ts = obj.get("timestamp", "")
            url = obj.get("url", "")
            try:
                nice = datetime.strptime(ts, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M")
            except Exception:
                nice = ts

            if source == "images":
                archive_url = f"https://web.archive.org/web/{ts}/{url}"
                row = {"source": source, "year": year, "timestamp": ts, "date": nice,
                       "original_url": url, "archive_url": archive_url, "matching_paragraph": "[IMAGE]"}
                writer.writerow(row)
                self.add_result_row(source, year, nice, url, "[IMAGE]", archive_url)
                hits += 1
                time.sleep(delay * 0.35)
                continue

            try:
                content = obj.text
            except Exception:
                time.sleep(delay)
                continue

            if content and eval_expr(tree, content):
                paragraph = extract_full_paragraph(content, tree)
                archive_url = (f"https://web.archive.org/web/{ts}/{url}" if source == "wayback"
                               else f"{obj.get('filename','')}#{obj.get('offset','')}")
                row = {"source": source, "year": year, "timestamp": ts, "date": nice,
                       "original_url": url, "archive_url": archive_url, "matching_paragraph": paragraph}
                writer.writerow(row)
                self.add_result_row(source, year, nice, url, paragraph, archive_url)
                hits += 1
                self.log(f"  HIT: {url[:65]}...")

            time.sleep(delay)

        self.log(f"  → {hits} hits")
        return hits


if __name__ == "__main__":
    app = LiveLeakSearchApp()
    app.mainloop()
