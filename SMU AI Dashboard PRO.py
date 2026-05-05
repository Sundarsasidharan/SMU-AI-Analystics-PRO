import customtkinter as ctk
from tkinter import filedialog, messagebox, colorchooser
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.patches import FancyBboxPatch
import matplotlib.cm as cm
import seaborn as sns
from PIL import Image
import os
import threading
import json
import urllib.request
import urllib.error
import time
import math
import re
from datetime import datetime
import io

# ─────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
app = ctk.CTk()
app.geometry("1600x950")
app.title("SMU AI Dashboard Pro ✦ v3.0")

# ─────────────────────────────────────────────
#  GLOBALS
# ─────────────────────────────────────────────
df            = None
cleaned_df    = None
processed_df  = None
chart_color   = "#00d4ff"
chart_color2  = "#ff6b6b"
main_frame    = None
chat_history  = []
current_fig   = None
active_btn    = None
animation_running = False

# ─────────────────────────────────────────────
#  PREMIUM COLOR PALETTE
# ─────────────────────────────────────────────
BG_DARK    = "#07070f"
BG_CARD    = "#0e0e1e"
BG_SIDEBAR = "#09091a"
ACCENT     = "#00d4ff"
ACCENT2    = "#7c3aed"
ACCENT3    = "#f59e0b"
TEXT_DIM   = "#6677aa"
TEXT_MAIN  = "#d0d8ff"
SUCCESS    = "#10b981"
WARNING    = "#f59e0b"
ERROR      = "#ef4444"
BORDER     = "#1a1a3a"
GRADIENT1  = "#00d4ff"
GRADIENT2  = "#7c3aed"

# ─────────────────────────────────────────────
#  BACKGROUND
# ─────────────────────────────────────────────
bg_label = ctk.CTkLabel(app, text="")
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

def set_default_bg():
    try:
        img    = Image.open("bg.png").resize((1600, 950))
        bg_img = ctk.CTkImage(light_image=img, dark_image=img, size=(1600, 950))
        bg_label.configure(image=bg_img)
        bg_label.image = bg_img
    except Exception:
        pass

set_default_bg()

# ─────────────────────────────────────────────
#  LAYOUT FRAMES
# ─────────────────────────────────────────────
sidebar = ctk.CTkFrame(app, width=220, corner_radius=0,
                       fg_color=BG_SIDEBAR,
                       border_width=1, border_color=BORDER)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

main_frame = ctk.CTkFrame(app, fg_color=BG_DARK, corner_radius=0)
main_frame.pack(side="right", fill="both", expand=True)

# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────
def clear_main():
    for w in main_frame.winfo_children():
        w.destroy()

def check_df():
    if df is None:
        messagebox.showwarning("⚠️ Warning", "முதல்ல Data Upload பண்ணு!")
        return False
    return True

def make_section_header(parent, title):
    f = ctk.CTkFrame(parent, fg_color="transparent")
    f.pack(anchor="w", pady=(14, 4), padx=15, fill="x")
    ctk.CTkLabel(f, text=title, font=("Segoe UI", 13, "bold"),
                 text_color=ACCENT).pack(anchor="w")
    ctk.CTkFrame(f, height=1, fg_color=ACCENT, corner_radius=0).pack(fill="x", pady=(3,0))

def make_info_card(parent, text, color=TEXT_MAIN):
    ctk.CTkLabel(parent, text=text, font=("Consolas", 11),
                 text_color=color, justify="left",
                 wraplength=960).pack(anchor="w", padx=20, pady=1)

def show_toast(message, color=SUCCESS):
    toast = ctk.CTkLabel(app, text=message,
                         font=("Segoe UI", 12, "bold"),
                         text_color="white",
                         fg_color=color,
                         corner_radius=10,
                         padx=18, pady=8)
    toast.place(relx=0.5, rely=0.93, anchor="center")
    app.after(2800, toast.destroy)

def set_active_btn(btn):
    global active_btn
    if active_btn:
        try:
            active_btn.configure(fg_color="#0f0f22")
        except Exception:
            pass
    active_btn = btn
    btn.configure(fg_color=ACCENT2)

def run_in_thread(fn):
    t = threading.Thread(target=fn, daemon=True)
    t.start()

def page_title(text, icon=""):
    f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                     corner_radius=14,
                     border_width=1, border_color=BORDER)
    f.pack(fill="x", padx=20, pady=(18, 8))
    ctk.CTkLabel(f, text=f"{icon}  {text}" if icon else text,
                 font=("Segoe UI", 22, "bold"),
                 text_color=ACCENT).pack(side="left", pady=14, padx=20)
    if df is not None:
        shape_lbl = ctk.CTkLabel(f, text=f"  {df.shape[0]:,} rows  ×  {df.shape[1]} cols",
                     font=("Segoe UI", 11),
                     text_color=TEXT_DIM)
        shape_lbl.pack(side="right", padx=20)

# ─────────────────────────────────────────────
#  ANIMATED SPINNER / PROGRESS
# ─────────────────────────────────────────────
def create_loading_label(parent, text="Processing..."):
    lbl = ctk.CTkLabel(parent, text=f"⏳  {text}",
                       font=("Segoe UI", 13), text_color=ACCENT2)
    lbl.pack(pady=8)
    spinners = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    idx = [0]
    def spin():
        if lbl.winfo_exists():
            lbl.configure(text=f"{spinners[idx[0] % len(spinners)]}  {text}")
            idx[0] += 1
            lbl.after(100, spin)
    spin()
    return lbl

# ─────────────────────────────────────────────
#  1. UPLOAD  (Enhanced with profiling)
# ─────────────────────────────────────────────
def upload_data():
    global df
    path = filedialog.askopenfilename(
        filetypes=[("CSV Files","*.csv"), ("Excel Files","*.xlsx"), ("JSON Files","*.json")]
    )
    if not path:
        return
    try:
        if path.endswith(".csv"):
            df = pd.read_csv(path, dtype=str)
        elif path.endswith(".xlsx"):
            df = pd.read_excel(path, dtype=str)
        elif path.endswith(".json"):
            df = pd.read_json(path).astype(str)

        clear_main()
        page_title("Data Upload & Profile", "📤")

        # Animated stats cards
        stats_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=6)

        mem_usage = df.memory_usage(deep=True).sum() / 1024
        cards = [
            ("Rows",    f"{df.shape[0]:,}",    ACCENT,  "📋"),
            ("Columns", f"{df.shape[1]}",       ACCENT2, "🗂️"),
            ("Nulls",   f"{df.isnull().sum().sum():,}", WARNING, "❓"),
            ("Dups",    f"{df.duplicated().sum():,}",   ERROR,   "🔁"),
            ("Memory",  f"{mem_usage:.1f} KB",  SUCCESS, "💾"),
        ]
        for label, val, color, icon in cards:
            c = ctk.CTkFrame(stats_frame, fg_color=BG_CARD,
                             corner_radius=12,
                             border_width=1, border_color=BORDER)
            c.pack(side="left", padx=5, expand=True, fill="x")
            ctk.CTkLabel(c, text=icon, font=("Segoe UI", 20)).pack(pady=(10, 0))
            ctk.CTkLabel(c, text=val, font=("Segoe UI", 22, "bold"),
                         text_color=color).pack(pady=(0, 2))
            ctk.CTkLabel(c, text=label, font=("Segoe UI", 10),
                         text_color=TEXT_DIM).pack(pady=(0, 10))

        # Tabs: Preview + Data Types + Quick Profile
        tab_frame = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                                  corner_radius=10, border_width=1, border_color=BORDER)
        tab_frame.pack(fill="x", padx=20, pady=4)

        content = ctk.CTkScrollableFrame(main_frame, fg_color=BG_CARD,
                                          corner_radius=10, height=440)
        content.pack(fill="both", expand=True, padx=20, pady=6)

        def show_preview():
            for w in content.winfo_children(): w.destroy()
            headers = list(df.columns[:10])
            for c_idx, col in enumerate(headers):
                ctk.CTkLabel(content, text=col,
                             font=("Segoe UI", 10, "bold"),
                             width=120, fg_color=ACCENT2,
                             text_color="white", corner_radius=6
                             ).grid(row=0, column=c_idx, padx=2, pady=2, sticky="ew")
            for r, (_, row) in enumerate(df.head(20).iterrows(), start=1):
                bg = BG_CARD if r % 2 == 0 else "#101025"
                for c_idx, col in enumerate(headers):
                    val = str(row[col])[:18]
                    ctk.CTkLabel(content, text=val,
                                 font=("Consolas", 10),
                                 width=120, fg_color=bg,
                                 text_color=TEXT_MAIN, corner_radius=3
                                 ).grid(row=r, column=c_idx, padx=2, pady=1, sticky="ew")

        def show_dtypes():
            for w in content.winfo_children(): w.destroy()
            ctk.CTkLabel(content, text=f"  {'Column':<35} {'Dtype':<15} {'Non-Null':>10} {'Unique':>10} {'Sample'}",
                         font=("Consolas", 11, "bold"), text_color=ACCENT,
                         justify="left").pack(anchor="w", padx=10, pady=6)
            ctk.CTkFrame(content, height=1, fg_color=BORDER).pack(fill="x", padx=10)
            for col in df.columns:
                nn = df[col].notna().sum()
                uu = df[col].nunique()
                samp = str(df[col].dropna().iloc[0])[:20] if nn > 0 else "N/A"
                ctk.CTkLabel(content,
                             text=f"  {col:<35} {str(df[col].dtype):<15} {nn:>10,} {uu:>10,}   {samp}",
                             font=("Consolas", 10), text_color=TEXT_MAIN,
                             justify="left").pack(anchor="w", padx=10, pady=1)

        def show_profile():
            for w in content.winfo_children(): w.destroy()
            num_df = df.select_dtypes(include="number") if df is not None else pd.DataFrame()
            if not num_df.empty:
                ctk.CTkLabel(content, text="  Quick Numeric Profile",
                             font=("Segoe UI", 13, "bold"), text_color=ACCENT
                             ).pack(anchor="w", padx=10, pady=8)
                hdr = f"  {'Column':<25} {'Min':>10} {'Max':>10} {'Mean':>10} {'Null%':>8}"
                ctk.CTkLabel(content, text=hdr, font=("Consolas", 11, "bold"),
                             text_color=ACCENT, justify="left").pack(anchor="w", padx=10)
                for col in num_df.columns:
                    mn   = round(float(num_df[col].min()), 2)
                    mx   = round(float(num_df[col].max()), 2)
                    mean = round(float(num_df[col].mean()), 2)
                    null_pct = round(df[col].isnull().sum() / len(df) * 100, 1)
                    color = WARNING if null_pct > 5 else TEXT_MAIN
                    ctk.CTkLabel(content,
                                 text=f"  {col:<25} {mn:>10} {mx:>10} {mean:>10} {null_pct:>7}%",
                                 font=("Consolas", 10), text_color=color,
                                 justify="left").pack(anchor="w", padx=10, pady=1)
            else:
                ctk.CTkLabel(content, text="No numeric columns found.",
                             text_color=TEXT_DIM).pack(pady=20)

        for name, fn in [("📋 Preview", show_preview), ("🗂️ Dtypes", show_dtypes), ("📊 Profile", show_profile)]:
            ctk.CTkButton(tab_frame, text=name, command=fn,
                          fg_color="#1a1a3a", hover_color=ACCENT2,
                          font=("Segoe UI", 12, "bold"),
                          width=140, height=36, corner_radius=8
                          ).pack(side="left", padx=6, pady=8)

        show_preview()
        show_toast(f"✅  Loaded {df.shape[0]:,} rows × {df.shape[1]} columns")

    except Exception as e:
        messagebox.showerror("Error", f"❌ {e}")

# ─────────────────────────────────────────────
#  2. CLEANING  (Enhanced)
# ─────────────────────────────────────────────
def clean_data():
    global df, cleaned_df
    if not check_df(): return
    clear_main()
    page_title("Data Cleaning Studio", "🧹")

    b_null = df.isnull().sum().sum()
    b_dup  = df.duplicated().sum()

    info_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                           corner_radius=10, border_width=1, border_color=BORDER)
    info_f.pack(fill="x", padx=20, pady=5)

    stats_row = ctk.CTkFrame(info_f, fg_color="transparent")
    stats_row.pack(fill="x", padx=15, pady=10)
    for label, val, color in [("Before Nulls", str(b_null), WARNING),
                                ("Before Dups", str(b_dup), ERROR),
                                ("Rows", f"{df.shape[0]:,}", ACCENT),
                                ("Cols", str(df.shape[1]), ACCENT2)]:
        c = ctk.CTkFrame(stats_row, fg_color="#141430", corner_radius=8)
        c.pack(side="left", padx=8, pady=4)
        ctk.CTkLabel(c, text=val, font=("Segoe UI", 18, "bold"),
                     text_color=color).pack(padx=14, pady=(8,2))
        ctk.CTkLabel(c, text=label, font=("Segoe UI", 10),
                     text_color=TEXT_DIM).pack(padx=14, pady=(0,8))

    # Options frame
    opts_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                           corner_radius=10, border_width=1, border_color=BORDER)
    opts_f.pack(fill="x", padx=20, pady=4)
    opts_row = ctk.CTkFrame(opts_f, fg_color="transparent")
    opts_row.pack(fill="x", padx=15, pady=8)

    remove_dup_var  = ctk.BooleanVar(value=True)
    fill_null_var   = ctk.BooleanVar(value=True)
    strip_ws_var    = ctk.BooleanVar(value=True)
    title_case_var  = ctk.BooleanVar(value=True)
    drop_high_null  = ctk.BooleanVar(value=False)

    for text, var in [("Remove Duplicates", remove_dup_var),
                       ("Fill Nulls", fill_null_var),
                       ("Strip Whitespace", strip_ws_var),
                       ("Title Case Cats", title_case_var),
                       ("Drop >50% Null Cols", drop_high_null)]:
        ctk.CTkCheckBox(opts_row, text=text, variable=var,
                        font=("Segoe UI", 11), text_color=TEXT_MAIN,
                        fg_color=ACCENT2, checkbox_width=18, checkbox_height=18
                        ).pack(side="left", padx=10, pady=4)

    log_box = ctk.CTkTextbox(main_frame, height=300,
                              font=("Consolas", 11),
                              fg_color=BG_CARD, text_color=TEXT_MAIN,
                              border_width=1, border_color=BORDER, corner_radius=10)
    log_box.pack(pady=8, padx=20, fill="both", expand=True)

    progress = ctk.CTkProgressBar(main_frame, progress_color=ACCENT2, height=8)
    progress.pack(fill="x", padx=20, pady=4)
    progress.set(0)

    def run_cleaning():
        global df, cleaned_df
        log = []
        cleaned_df = df.copy()
        steps = 5
        step = 0

        if drop_high_null.get():
            thresh = len(cleaned_df) * 0.5
            cols_before = cleaned_df.shape[1]
            cleaned_df.dropna(thresh=thresh, axis=1, inplace=True)
            log.append(f"✅ Dropped high-null cols    : {cols_before - cleaned_df.shape[1]} columns removed")
        step += 1; app.after(0, lambda s=step/steps: progress.set(s))

        if remove_dup_var.get():
            before = len(cleaned_df)
            cleaned_df.drop_duplicates(inplace=True)
            log.append(f"✅ Duplicates removed        : {before - len(cleaned_df)}")
        step += 1; app.after(0, lambda s=step/steps: progress.set(s))

        if strip_ws_var.get():
            for col in cleaned_df.select_dtypes(include="object").columns:
                cleaned_df[col] = cleaned_df[col].str.strip()
            cleaned_df.columns = cleaned_df.columns.str.strip()
            log.append("✅ Whitespace stripped        : Done")
        step += 1; app.after(0, lambda s=step/steps: progress.set(s))

        if fill_null_var.get():
            for col in cleaned_df.columns:
                n = cleaned_df[col].isnull().sum()
                if n > 0:
                    if cleaned_df[col].dtype == "object":
                        cleaned_df[col].fillna("Unknown", inplace=True)
                    else:
                        cleaned_df[col].fillna(cleaned_df[col].median(), inplace=True)
                    log.append(f"✅ Filled nulls [{col[:30]}]  : {n} values")
        step += 1; app.after(0, lambda s=step/steps: progress.set(s))

        if title_case_var.get():
            for col in ["Ship Mode","Segment","Region","Category","Sub-Category"]:
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].str.title()
            log.append("✅ Title case applied         : Standard columns")

        a_null = cleaned_df.isnull().sum().sum()
        a_dup  = cleaned_df.duplicated().sum()
        log.append(f"\n📊 After  →  Nulls: {a_null}   |   Duplicates: {a_dup}")
        log.append(f"📐 Shape  →  {cleaned_df.shape[0]:,} rows × {cleaned_df.shape[1]} cols")
        log.append("🎉 Cleaning Complete!")

        df = cleaned_df.copy()
        app.after(0, lambda: progress.set(1.0))
        app.after(0, lambda: log_box.delete("1.0","end"))
        app.after(0, lambda: log_box.insert("end", "\n".join(log)))
        app.after(0, lambda: show_toast("✅ Data cleaned successfully!"))

    def threaded_clean():
        run_btn.configure(state="disabled", text="⏳ Cleaning...")
        run_in_thread(lambda: (run_cleaning(),
                               app.after(0, lambda: run_btn.configure(state="normal", text="▶   Run Cleaning"))))

    run_btn = ctk.CTkButton(main_frame, text="▶   Run Cleaning",
                  command=threaded_clean,
                  fg_color=ACCENT2, hover_color="#6d28d9",
                  font=("Segoe UI", 14, "bold"),
                  width=220, height=46, corner_radius=12)
    run_btn.pack(pady=10)

# ─────────────────────────────────────────────
#  3. PROCESSING
# ─────────────────────────────────────────────
def process_data():
    global df, processed_df
    if not check_df(): return
    clear_main()
    page_title("Data Processing", "⚙️")

    log_box = ctk.CTkTextbox(main_frame, height=420,
                              font=("Consolas", 11),
                              fg_color=BG_CARD, text_color=TEXT_MAIN,
                              border_width=1, border_color=BORDER, corner_radius=10)
    log_box.pack(pady=8, padx=20, fill="both", expand=True)
    log_box.insert("end", "Click ▶ Run Processing to begin...\n")

    progress = ctk.CTkProgressBar(main_frame, progress_color=SUCCESS, height=8)
    progress.pack(fill="x", padx=20, pady=4)
    progress.set(0)

    def run_processing():
        global df, processed_df
        log = []
        try:
            processed_df = df.copy()
            total_cols = len(processed_df.columns)
            converted = 0

            for col in ["Order Date","Ship Date","Date","order_date","date"]:
                if col in processed_df.columns:
                    processed_df[col] = pd.to_datetime(processed_df[col], errors="coerce")
                    log.append(f"✅ {col:<28} → datetime")

            for col in ["Sales","Quantity","Discount","Profit","Postal Code","Row ID",
                        "Price","Revenue","Cost","Amount"]:
                if col in processed_df.columns:
                    processed_df[col] = pd.to_numeric(processed_df[col], errors="coerce")
                    log.append(f"✅ {col:<28} → numeric")
                    converted += 1
                    app.after(0, lambda v=converted/max(total_cols,1): progress.set(min(v,1)))

            for col in ["Order ID","Customer ID","Product ID"]:
                if col in processed_df.columns:
                    processed_df[col] = processed_df[col].astype(str)

            # Auto-detect & convert remaining
            for col in processed_df.select_dtypes("object").columns:
                try:
                    test = pd.to_numeric(processed_df[col], errors="coerce")
                    if test.notna().sum() > len(processed_df) * 0.8:
                        processed_df[col] = test
                        log.append(f"🔍 Auto-detected numeric     : {col}")
                except:
                    pass

            processed_df = processed_df.ffill()
            log.append(f"\n📐 Final Shape : {processed_df.shape}")
            dtypes_summary = processed_df.dtypes.value_counts()
            for dtype, cnt in dtypes_summary.items():
                log.append(f"   • {str(dtype):<15} : {cnt} columns")
            log.append("\n🎉 Processing Complete!")
            df = processed_df.copy()

        except Exception as e:
            log.append(f"\n❌ Error: {e}")

        app.after(0, lambda: progress.set(1.0))
        app.after(0, lambda: log_box.delete("1.0","end"))
        app.after(0, lambda: log_box.insert("end", "\n".join(log)))
        app.after(0, lambda: show_toast("✅ Processing complete!"))

    def threaded_run():
        run_btn.configure(state="disabled", text="⏳ Running...")
        run_in_thread(lambda: (run_processing(),
                               app.after(0, lambda: run_btn.configure(state="normal", text="▶   Run Processing"))))

    run_btn = ctk.CTkButton(main_frame, text="▶   Run Processing",
                             command=threaded_run,
                             fg_color=ACCENT2, hover_color="#6d28d9",
                             font=("Segoe UI", 14, "bold"),
                             width=240, height=46, corner_radius=12)
    run_btn.pack(pady=12)

# ─────────────────────────────────────────────
#  4. EDA  (Enhanced)
# ─────────────────────────────────────────────
def eda():
    if not check_df(): return
    clear_main()
    page_title("Exploratory Data Analysis", "📊")

    tab_frame = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                              corner_radius=10, border_width=1, border_color=BORDER)
    tab_frame.pack(fill="x", padx=20, pady=4)

    scroll = ctk.CTkScrollableFrame(main_frame, fg_color=BG_CARD,
                                     corner_radius=10, height=590)
    scroll.pack(padx=20, pady=5, fill="both", expand=True)

    def show_overview():
        for w in scroll.winfo_children(): w.destroy()
        make_section_header(scroll, "📐 Dataset Shape")
        make_info_card(scroll, f"Rows: {df.shape[0]:,}   |   Columns: {df.shape[1]}")
        make_info_card(scroll, f"Memory: {df.memory_usage(deep=True).sum()/1024:.2f} KB")

        make_section_header(scroll, "📋 Columns & Data Types")
        for col in df.columns:
            make_info_card(scroll, f"  • {col:<35} {str(df[col].dtype)}")

        make_section_header(scroll, "❓ Missing Values")
        null_counts = df.isnull().sum()
        if null_counts.sum() == 0:
            make_info_card(scroll, "  ✅ No missing values!", SUCCESS)
        else:
            for col, cnt in null_counts.items():
                if cnt > 0:
                    pct = round(cnt / len(df) * 100, 2)
                    bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                    make_info_card(scroll, f"  • {col:<35} {cnt:>6} missing  ({pct:.1f}%)  [{bar}]", WARNING)

        make_section_header(scroll, "🔁 Duplicates")
        dup = df.duplicated().sum()
        make_info_card(scroll, f"  Duplicate rows: {dup}", ERROR if dup > 0 else SUCCESS)

    def show_stats():
        for w in scroll.winfo_children(): w.destroy()
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            make_section_header(scroll, "🔢 Numeric Statistics")
            hdr = f"  {'Column':<25} {'Min':>10} {'Max':>10} {'Mean':>10} {'Median':>10} {'Std':>10} {'Skew':>8}"
            make_info_card(scroll, hdr, ACCENT)
            make_info_card(scroll, "  " + "─" * 90, BORDER)
            for col in num_df.columns:
                mn   = round(num_df[col].min(), 2)
                mx   = round(num_df[col].max(), 2)
                mean = round(num_df[col].mean(), 2)
                med  = round(num_df[col].median(), 2)
                std  = round(num_df[col].std(), 2)
                skew = round(float(num_df[col].skew()), 2)
                flag = "  ⚠️ skewed" if abs(skew) > 1 else ""
                row_color = WARNING if abs(skew) > 1 else TEXT_MAIN
                make_info_card(scroll,
                    f"  {col:<25} {mn:>10} {mx:>10} {mean:>10} {med:>10} {std:>10} {skew:>8}{flag}",
                    row_color)

        make_section_header(scroll, "📉 Outlier Detection (IQR)")
        for col in num_df.columns:
            Q1  = num_df[col].quantile(0.25)
            Q3  = num_df[col].quantile(0.75)
            IQR = Q3 - Q1
            outliers = ((num_df[col] < Q1 - 1.5*IQR) | (num_df[col] > Q3 + 1.5*IQR)).sum()
            pct = round(outliers / len(num_df) * 100, 1)
            make_info_card(scroll,
                f"  • {col:<30} {outliers:>5} outliers  ({pct}%)",
                WARNING if outliers > 0 else SUCCESS)

    def show_categorical():
        for w in scroll.winfo_children(): w.destroy()
        cat_df = df.select_dtypes(include="object")
        if cat_df.empty:
            make_info_card(scroll, "No categorical columns found.", TEXT_DIM)
            return
        make_section_header(scroll, "🏷️ Categorical Columns Overview")
        for col in cat_df.columns:
            unique = df[col].nunique()
            top    = df[col].value_counts().index[0] if unique > 0 else "N/A"
            top_n  = df[col].value_counts().iloc[0]
            make_info_card(scroll,
                f"  • {col:<30}  Unique: {unique:<6}  Top: '{top}' ({top_n:,})")

        make_section_header(scroll, "📊 Top Value Counts (per column)")
        for col in cat_df.columns[:6]:
            make_info_card(scroll, f"\n  ── {col} ──", ACCENT2)
            for val, cnt in df[col].value_counts().head(5).items():
                bar_len = int(cnt / df[col].value_counts().iloc[0] * 30)
                bar = "█" * bar_len
                make_info_card(scroll, f"    {str(val):<30}  {cnt:>6,}  {bar}")

    def show_correlation():
        for w in scroll.winfo_children(): w.destroy()
        num_df = df.select_dtypes(include="number")
        if num_df.shape[1] < 2:
            make_info_card(scroll, "Need ≥ 2 numeric columns for correlation.", WARNING)
            return
        make_section_header(scroll, "🔗 Correlation Matrix (Top Pairs)")
        corr = num_df.corr().abs()
        pairs = []
        cols = corr.columns.tolist()
        for i in range(len(cols)):
            for j in range(i+1, len(cols)):
                pairs.append((cols[i], cols[j], round(corr.iloc[i,j], 4)))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        make_info_card(scroll,
            f"  {'Column A':<25} {'Column B':<25} {'Corr':>8}  Strength", ACCENT)
        make_info_card(scroll, "  " + "─" * 72, BORDER)
        for a, b, c in pairs[:20]:
            strength = "🔴 Strong" if abs(c)>0.7 else ("🟡 Moderate" if abs(c)>0.4 else "🟢 Weak")
            color = ERROR if abs(c)>0.7 else (WARNING if abs(c)>0.4 else SUCCESS)
            make_info_card(scroll, f"  {a:<25} {b:<25} {c:>8}  {strength}", color)

    def show_advanced():
        for w in scroll.winfo_children(): w.destroy()
        make_section_header(scroll, "🧮 Advanced Statistics")
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            for col in num_df.columns:
                kurt = round(float(num_df[col].kurt()), 3)
                q1   = round(float(num_df[col].quantile(0.25)), 2)
                q3   = round(float(num_df[col].quantile(0.75)), 2)
                iqr  = round(q3 - q1, 2)
                cv   = round(float(num_df[col].std() / num_df[col].mean() * 100), 2) if num_df[col].mean() != 0 else 0
                make_info_card(scroll,
                    f"  {col:<25}  Kurtosis: {kurt:>8}  Q1: {q1:>10}  Q3: {q3:>10}  IQR: {iqr:>8}  CV%: {cv:>6}",
                    TEXT_MAIN)

    tabs = [("Overview", show_overview), ("Statistics", show_stats),
            ("Categorical", show_categorical), ("Correlation", show_correlation),
            ("Advanced", show_advanced)]

    for name, fn in tabs:
        ctk.CTkButton(tab_frame, text=name, command=fn,
                      fg_color="#1a1a3a", hover_color=ACCENT2,
                      font=("Segoe UI", 12, "bold"),
                      width=130, height=36, corner_radius=8).pack(side="left", padx=6, pady=8)

    show_overview()

# ─────────────────────────────────────────────
#  5. FEATURE ENGINEERING  (Enhanced)
# ─────────────────────────────────────────────
def feature_engineering():
    global df
    if not check_df(): return
    clear_main()
    page_title("Feature Engineering", "🔧")

    # Custom feature creator
    custom_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                             corner_radius=10, border_width=1, border_color=BORDER)
    custom_f.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(custom_f, text="➕  Custom Feature  (e.g.  Sales * Quantity)",
                 font=("Segoe UI", 12), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10,2))
    cust_row = ctk.CTkFrame(custom_f, fg_color="transparent")
    cust_row.pack(fill="x", padx=15, pady=(0,10))
    cust_name = ctk.CTkEntry(cust_row, placeholder_text="New column name",
                              width=180, height=34, font=("Segoe UI",11), fg_color="#1a1a3a")
    cust_name.pack(side="left", padx=4)
    cust_expr = ctk.CTkEntry(cust_row, placeholder_text="Expression using df column names",
                              width=400, height=34, font=("Segoe UI",11), fg_color="#1a1a3a")
    cust_expr.pack(side="left", padx=4)
    def add_custom_feature():
        global df
        name = cust_name.get().strip()
        expr = cust_expr.get().strip()
        if not name or not expr:
            show_toast("⚠️ Enter name & expression", WARNING)
            return
        try:
            df[name] = df.eval(expr)
            show_toast(f"✅ Added '{name}'")
            log_box.insert("end", f"✅ Custom feature '{name}' = {expr}\n")
        except Exception as e:
            show_toast(f"❌ {e}", ERROR)
    ctk.CTkButton(cust_row, text="Add Feature",
                  command=add_custom_feature,
                  fg_color=ACCENT2, hover_color="#6d28d9",
                  font=("Segoe UI", 12, "bold"),
                  width=130, height=34, corner_radius=8).pack(side="left", padx=8)

    log_box = ctk.CTkTextbox(main_frame, height=300,
                              font=("Consolas", 11),
                              fg_color=BG_CARD, text_color=TEXT_MAIN,
                              border_width=1, border_color=BORDER, corner_radius=10)
    log_box.pack(pady=5, padx=20, fill="both", expand=True)
    log_box.insert("end", "Click ▶ Run Auto Feature Engineering to begin...\n")

    def run_fe():
        global df
        log = []
        try:
            df["Order Date"] = pd.to_datetime(df.get("Order Date", pd.Series(dtype=str)), errors="coerce")
            df["Ship Date"]  = pd.to_datetime(df.get("Ship Date", pd.Series(dtype=str)),  errors="coerce")
            if "Order Date" in df.columns and df["Order Date"].notna().sum() > 0:
                df["Order_Year"]      = df["Order Date"].dt.year
                df["Order_Month"]     = df["Order Date"].dt.month
                df["Order_Quarter"]   = df["Order Date"].dt.quarter
                df["Order_DayOfWeek"] = df["Order Date"].dt.dayofweek
                df["Order_WeekNum"]   = df["Order Date"].dt.isocalendar().week.astype(int)
                df["Is_Weekend"]      = (df["Order Date"].dt.dayofweek >= 5).astype(int)
                log.append("✅ Date Features   : Year, Month, Quarter, DayOfWeek, WeekNum, Is_Weekend")
            if "Ship Date" in df.columns and df["Ship Date"].notna().sum() > 0:
                df["Delivery_Days"]   = (df["Ship Date"] - df["Order Date"]).dt.days
                log.append("✅ Delivery_Days   : Added")
        except Exception as e:
            log.append(f"⚠️  Date Features skipped: {e}")

        try:
            for col in ["Sales","Profit","Quantity","Discount"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "Profit" in df.columns and "Sales" in df.columns:
                df["Profit_Margin"]    = (df["Profit"] / df["Sales"] * 100).round(2)
                df["Is_Profitable"]    = (df["Profit"] > 0).astype(int)
                log.append("✅ Profit features : Profit_Margin, Is_Profitable")
            if "Sales" in df.columns and "Quantity" in df.columns:
                df["Revenue_per_Unit"] = (df["Sales"] / df["Quantity"]).round(2)
                log.append("✅ Revenue_per_Unit: Added")
            if "Delivery_Days" in df.columns:
                df["Is_Late"]          = (df["Delivery_Days"] > 5).astype(int)
                log.append("✅ Is_Late         : Added")
            if "Sales" in df.columns:
                df["Is_High_Value"]    = (df["Sales"] > df["Sales"].median()).astype(int)
                df["Sales_Log"]        = np.log1p(df["Sales"])
                df["Sales_Category"]   = pd.cut(df["Sales"],
                    bins=[0,100,500,1000,99999], labels=["Low","Medium","High","Very High"])
                log.append("✅ Sales features  : Is_High_Value, Sales_Log, Sales_Category")
            # Z-score outlier flag for all numerics
            for col in df.select_dtypes("number").columns:
                z = (df[col] - df[col].mean()) / (df[col].std() + 1e-9)
                df[f"{col}_IsOutlier"] = (z.abs() > 3).astype(int)
            log.append("✅ Outlier Flags    : Z-score based flags for all numeric cols")
        except Exception as e:
            log.append(f"⚠️  Feature error: {e}")

        log.append(f"\n📐 New Shape: {df.shape[0]:,} rows × {df.shape[1]} cols")
        log.append("🎉 Feature Engineering Complete!")
        app.after(0, lambda: log_box.delete("1.0","end"))
        app.after(0, lambda: log_box.insert("end", "\n".join(log)))
        app.after(0, lambda: show_toast("✅ Features engineered!"))

    def threaded_fe():
        run_btn.configure(state="disabled", text="⏳ Running...")
        run_in_thread(lambda: (run_fe(),
                               app.after(0, lambda: run_btn.configure(state="normal", text="▶   Run Feature Engineering"))))

    run_btn = ctk.CTkButton(main_frame, text="▶   Run Auto Feature Engineering",
                  command=threaded_fe,
                  fg_color=ACCENT2, hover_color="#6d28d9",
                  font=("Segoe UI", 14, "bold"),
                  width=300, height=46, corner_radius=12)
    run_btn.pack(pady=10)

# ─────────────────────────────────────────────
#  6. VISUALIZATION  (Advanced with Animations)
# ─────────────────────────────────────────────
def visualize():
    global chart_color, chart_color2, current_fig
    if not check_df(): return
    clear_main()
    page_title("Advanced Visualization Studio", "📈")

    chart_types = [
        "Bar Chart", "Grouped Bar", "Stacked Bar", "Line Chart", "Multi-Line",
        "Pie Chart", "Donut Chart", "Scatter Plot", "Bubble Chart", "Histogram",
        "Box Plot", "Heatmap", "Area Chart", "Stacked Area", "Count Plot",
        "Violin Plot", "KDE Plot", "Regression Plot", "Step Chart", "Waterfall Chart",
        "Animated Bar Race", "Rolling Line", "Lollipop Chart"
    ]

    chart_var     = ctk.StringVar(value="Bar Chart")
    col_x_var     = ctk.StringVar()
    col_y_var     = ctk.StringVar()
    col_group_var = ctk.StringVar(value="None")
    col_size_var  = ctk.StringVar(value="None")
    title_var     = ctk.StringVar(value="")
    show_vals_var = ctk.BooleanVar(value=True)
    animate_var   = ctk.BooleanVar(value=True)
    log_scale_var = ctk.BooleanVar(value=False)
    theme_var     = ctk.StringVar(value="Dark Pro")

    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include="object").columns.tolist()
    all_cols = df.columns.tolist()

    if cat_cols:  col_x_var.set(cat_cols[0])
    elif all_cols: col_x_var.set(all_cols[0])
    if num_cols:  col_y_var.set(num_cols[0])
    elif all_cols: col_y_var.set(all_cols[0])

    # ─ Control panel ─
    ctrl = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                         corner_radius=10, border_width=1, border_color=BORDER)
    ctrl.pack(fill="x", padx=20, pady=5)

    def lbl(parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 10),
                     text_color=TEXT_DIM).pack(side="left", padx=(6,2))

    r1 = ctk.CTkFrame(ctrl, fg_color="transparent"); r1.pack(fill="x", padx=10, pady=(8,2))
    lbl(r1, "Chart:"); ctk.CTkComboBox(r1, values=chart_types, variable=chart_var,
                    width=150, font=("Segoe UI",10), fg_color="#1a1a3a",
                    button_color=ACCENT2).pack(side="left", padx=3)
    lbl(r1, "X:"); ctk.CTkComboBox(r1, values=all_cols, variable=col_x_var,
                    width=130, font=("Segoe UI",10), fg_color="#1a1a3a",
                    button_color=ACCENT2).pack(side="left", padx=3)
    lbl(r1, "Y:"); ctk.CTkComboBox(r1, values=num_cols if num_cols else all_cols,
                    variable=col_y_var, width=130, font=("Segoe UI",10),
                    fg_color="#1a1a3a", button_color=ACCENT2).pack(side="left", padx=3)
    lbl(r1, "Group:"); ctk.CTkComboBox(r1, values=["None"]+cat_cols, variable=col_group_var,
                    width=120, font=("Segoe UI",10), fg_color="#1a1a3a",
                    button_color=ACCENT2).pack(side="left", padx=3)
    lbl(r1, "Size:"); ctk.CTkComboBox(r1, values=["None"]+num_cols, variable=col_size_var,
                    width=120, font=("Segoe UI",10), fg_color="#1a1a3a",
                    button_color=ACCENT2).pack(side="left", padx=3)
    lbl(r1, "Theme:"); ctk.CTkComboBox(r1, values=["Dark Pro","Midnight Blue","Forest","Lava"],
                    variable=theme_var, width=110, font=("Segoe UI",10),
                    fg_color="#1a1a3a", button_color=ACCENT2).pack(side="left", padx=3)

    r2 = ctk.CTkFrame(ctrl, fg_color="transparent"); r2.pack(fill="x", padx=10, pady=(2,8))
    lbl(r2, "Title:"); ctk.CTkEntry(r2, textvariable=title_var, width=200, height=30,
                    font=("Segoe UI",10), placeholder_text="Chart title",
                    fg_color="#1a1a3a").pack(side="left", padx=3)
    ctk.CTkCheckBox(r2, text="Values", variable=show_vals_var,
                    checkbox_width=16, checkbox_height=16, fg_color=ACCENT2,
                    font=("Segoe UI",10)).pack(side="left", padx=6)
    ctk.CTkCheckBox(r2, text="Animate", variable=animate_var,
                    checkbox_width=16, checkbox_height=16, fg_color=SUCCESS,
                    font=("Segoe UI",10)).pack(side="left", padx=4)
    ctk.CTkCheckBox(r2, text="Log Scale", variable=log_scale_var,
                    checkbox_width=16, checkbox_height=16, fg_color=WARNING,
                    font=("Segoe UI",10)).pack(side="left", padx=4)

    color1_btn = ctk.CTkButton(r2, text="🎨 C1", fg_color=chart_color,
                                width=60, height=28, font=("Segoe UI",10), corner_radius=6)
    color1_btn.pack(side="left", padx=4)
    def pick_color1():
        global chart_color
        c = colorchooser.askcolor(color=chart_color, title="Pick Color 1")[1]
        if c: chart_color = c; color1_btn.configure(fg_color=c)
    color1_btn.configure(command=pick_color1)

    color2_btn = ctk.CTkButton(r2, text="🎨 C2", fg_color=chart_color2,
                                width=60, height=28, font=("Segoe UI",10), corner_radius=6)
    color2_btn.pack(side="left", padx=4)
    def pick_color2():
        global chart_color2
        c = colorchooser.askcolor(color=chart_color2, title="Pick Color 2")[1]
        if c: chart_color2 = c; color2_btn.configure(fg_color=c)
    color2_btn.configure(command=pick_color2)

    ctk.CTkButton(r2, text="📊 Draw", command=lambda: draw_chart(),
                  fg_color=ACCENT2, hover_color="#6d28d9",
                  font=("Segoe UI", 12, "bold"), width=110, height=30,
                  corner_radius=8).pack(side="left", padx=8)

    def save_chart(fmt):
        if current_fig is None:
            show_toast("⚠️ Draw a chart first!", WARNING); return
        path = filedialog.asksaveasfilename(defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()}", f"*.{fmt}")])
        if path:
            current_fig.savefig(path, format=fmt, dpi=180, bbox_inches="tight",
                                 facecolor=current_fig.get_facecolor())
            show_toast(f"✅ Saved as {fmt.upper()}!")

    for fmt, col in [("PNG","#1a3a2a"), ("JPEG","#1a2a3a"), ("SVG","#2a1a3a"), ("PDF","#1a1a1a")]:
        ctk.CTkButton(r2, text=fmt, command=lambda f=fmt: save_chart(f.lower()),
                      fg_color=col, hover_color=ACCENT2,
                      font=("Segoe UI", 10, "bold"), width=55, height=28,
                      corner_radius=6).pack(side="left", padx=2)

    # Chart canvas
    canvas_frame = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                                  corner_radius=10, border_width=1, border_color=BORDER)
    canvas_frame.pack(fill="both", expand=True, padx=20, pady=8)

    def get_theme_colors(theme):
        themes = {
            "Dark Pro":      {"bg": "#0e0e1e", "ax": "#0a0a18", "tick": "#aaaacc", "grid": "#1a1a3a", "palette": "Set2"},
            "Midnight Blue": {"bg": "#030518", "ax": "#050a20", "tick": "#8899dd", "grid": "#0a1030", "palette": "Blues"},
            "Forest":        {"bg": "#071408", "ax": "#040f04", "tick": "#88cc88", "grid": "#0a1a0a", "palette": "Greens"},
            "Lava":          {"bg": "#140503", "ax": "#100404", "tick": "#cc8866", "grid": "#1a0a08", "palette": "Reds"},
        }
        return themes.get(theme, themes["Dark Pro"])

    def style_ax(ax, theme_colors):
        ax.set_facecolor(theme_colors["ax"])
        ax.tick_params(colors=theme_colors["tick"], labelsize=9)
        ax.xaxis.label.set_color(theme_colors["tick"])
        ax.yaxis.label.set_color(theme_colors["tick"])
        for spine in ax.spines.values():
            spine.set_edgecolor("#222244")
        ax.grid(color=theme_colors["grid"], linestyle="--", linewidth=0.5, alpha=0.6)

    def draw_chart():
        global current_fig, animation_running
        for w in canvas_frame.winfo_children(): w.destroy()
        animation_running = False

        theme_colors = get_theme_colors(theme_var.get())
        bg = theme_colors["bg"]
        palette = theme_colors["palette"]

        fig, ax = plt.subplots(figsize=(12, 5.5), facecolor=bg)
        style_ax(ax, theme_colors)

        ct     = chart_var.get()
        cx     = col_x_var.get()
        cy     = col_y_var.get()
        grp    = col_group_var.get()
        size_c = col_size_var.get()
        clr    = chart_color
        clr2   = chart_color2
        title  = title_var.get() or f"{ct}  —  {cx}"
        show_v = show_vals_var.get()
        do_anim= animate_var.get()
        log_sc = log_scale_var.get()

        try:
            # ── BAR CHART ──────────────────────────────────────────
            if ct == "Bar Chart":
                if grp and grp != "None" and grp in df.columns:
                    data = df.groupby([cx, grp])[cy].sum().unstack(fill_value=0)
                    data.plot(kind="bar", ax=ax, colormap=palette, edgecolor="none")
                    ax.legend(title=grp, labelcolor="white", facecolor="#111128",
                              edgecolor=BORDER, fontsize=9)
                else:
                    data = (df.groupby(cx)[cy].sum().sort_values(ascending=False).head(15)
                            if cy in num_cols else df[cx].value_counts().head(15))
                    colors = sns.color_palette(palette, len(data))
                    bars = ax.bar(data.index.astype(str), data.values, color=colors,
                                  edgecolor="none", alpha=0.9)
                    if do_anim:
                        for bar_obj in bars:
                            bar_obj.set_height(0)
                        def anim_bars(frame):
                            for i, bar_obj in enumerate(bars):
                                target = data.values[i]
                                bar_obj.set_height(min(bar_obj.get_height() + target/20, target))
                        ani = animation.FuncAnimation(fig, anim_bars, frames=20, interval=40, repeat=False)
                        fig._anim = ani
                    if show_v:
                        for b in bars:
                            ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(data.values)*0.01,
                                    f"{b.get_height():,.0f}", ha="center", va="bottom",
                                    fontsize=8, color="white")
                plt.xticks(rotation=45, ha="right", color=theme_colors["tick"])

            # ── STACKED BAR ─────────────────────────────────────────
            elif ct == "Stacked Bar":
                if grp and grp != "None" and grp in df.columns:
                    data = df.groupby([cx, grp])[cy].sum().unstack(fill_value=0)
                    data.plot(kind="bar", stacked=True, ax=ax, colormap=palette, edgecolor="none")
                    ax.legend(title=grp, labelcolor="white", facecolor="#111128",
                              edgecolor=BORDER, fontsize=9)
                    plt.xticks(rotation=45, ha="right")
                else:
                    ax.text(0.5, 0.5, "Set 'Group By' for Stacked Bar",
                            ha="center", va="center", color="white", transform=ax.transAxes)

            # ── GROUPED BAR ──────────────────────────────────────────
            elif ct == "Grouped Bar":
                if grp and grp != "None" and grp in df.columns:
                    data = df.groupby(grp)[[cy]].sum()
                    bars = ax.bar(data.index.astype(str), data[cy], color=clr, edgecolor="none")
                    if show_v:
                        for b in bars:
                            ax.text(b.get_x()+b.get_width()/2, b.get_height()+max(data[cy].values)*0.01,
                                    f"{b.get_height():,.0f}", ha="center", va="bottom",
                                    fontsize=8, color="white")
                    ax.set_xlabel(grp); plt.xticks(rotation=45, ha="right")
                else:
                    ax.text(0.5, 0.5, "Set 'Group By' for Grouped Bar",
                            ha="center", va="center", color="white", transform=ax.transAxes)

            # ── LINE CHART ──────────────────────────────────────────
            elif ct == "Line Chart":
                data = df[cy].dropna().reset_index(drop=True)
                if do_anim:
                    line, = ax.plot([], [], color=clr, linewidth=2.5, alpha=0.9)
                    fill = ax.fill_between([], [], alpha=0.15, color=clr)
                    def init_line(): line.set_data([], []); return line,
                    def anim_line(frame):
                        x = list(range(int(frame * len(data) / 60)))
                        y = data.iloc[:len(x)].tolist()
                        line.set_data(x, y)
                        ax.set_xlim(0, len(data))
                        ax.set_ylim(data.min() * 0.9, data.max() * 1.1)
                        return line,
                    ani = animation.FuncAnimation(fig, anim_line, frames=60,
                                                   init_func=init_line, interval=30, blit=True)
                    fig._anim = ani
                else:
                    ax.plot(data, color=clr, linewidth=2.5, alpha=0.9)
                    ax.fill_between(range(len(data)), data, alpha=0.15, color=clr)
                ax.set_ylabel(cy)

            # ── MULTI-LINE ──────────────────────────────────────────
            elif ct == "Multi-Line":
                colors_ml = sns.color_palette(palette, len(num_cols[:6]))
                for i, col in enumerate(num_cols[:6]):
                    data = df[col].dropna().reset_index(drop=True)
                    ax.plot(data, color=colors_ml[i], linewidth=2, label=col, alpha=0.85)
                ax.legend(labelcolor="white", facecolor="#111128", edgecolor=BORDER)

            # ── PIE CHART ──────────────────────────────────────────
            elif ct == "Pie Chart":
                data = df[cx].value_counts().head(8)
                colors_pie = sns.color_palette(palette, len(data))
                wedges, texts, autotexts = ax.pie(
                    data.values, labels=data.index.astype(str),
                    autopct="%1.1f%%" if show_v else "",
                    startangle=140, colors=colors_pie,
                    pctdistance=0.82,
                    wedgeprops=dict(edgecolor="#0a0a18", linewidth=1.5))
                for t in autotexts: t.set_color("white"); t.set_fontsize(9)
                for t in texts: t.set_color("#cccccc"); t.set_fontsize(9)

            # ── DONUT CHART ─────────────────────────────────────────
            elif ct == "Donut Chart":
                data = df[cx].value_counts().head(8)
                colors_dn = sns.color_palette(palette, len(data))
                wedges, texts, autotexts = ax.pie(
                    data.values, labels=data.index.astype(str),
                    autopct="%1.1f%%" if show_v else "",
                    startangle=140, colors=colors_dn,
                    wedgeprops=dict(width=0.55, edgecolor="#0a0a18", linewidth=2))
                for t in autotexts: t.set_color("white"); t.set_fontsize(9)
                for t in texts: t.set_color("#cccccc"); t.set_fontsize(9)
                ax.text(0, 0, f"Total\n{data.sum():,}", ha="center", va="center",
                        color="white", fontsize=12, fontweight="bold")

            # ── SCATTER PLOT ─────────────────────────────────────────
            elif ct == "Scatter Plot":
                xd = pd.to_numeric(df[cx], errors="coerce")
                yd = pd.to_numeric(df[cy], errors="coerce")
                colors_sc = None
                if grp and grp != "None" and grp in df.columns:
                    cats = df[grp].astype("category")
                    cmap = cm.get_cmap(palette if palette != "Set2" else "tab10", cats.cat.codes.nunique())
                    colors_sc = [cmap(c) for c in cats.cat.codes]
                ax.scatter(xd, yd, alpha=0.55, c=colors_sc if colors_sc else clr,
                           s=22, edgecolors="none")
                ax.set_xlabel(cx); ax.set_ylabel(cy)

            # ── BUBBLE CHART ─────────────────────────────────────────
            elif ct == "Bubble Chart":
                xd = pd.to_numeric(df[cx], errors="coerce")
                yd = pd.to_numeric(df[cy], errors="coerce")
                if size_c and size_c != "None" and size_c in df.columns:
                    sd = pd.to_numeric(df[size_c], errors="coerce").fillna(1)
                    sd = (sd - sd.min()) / (sd.max() - sd.min() + 1e-9) * 300 + 10
                else:
                    sd = 60
                ax.scatter(xd, yd, s=sd, alpha=0.5, c=clr, edgecolors=clr2, linewidth=0.5)
                ax.set_xlabel(cx); ax.set_ylabel(cy)

            # ── HISTOGRAM ──────────────────────────────────────────
            elif ct == "Histogram":
                data = pd.to_numeric(df[cx], errors="coerce").dropna()
                n, bins, patches = ax.hist(data, bins=30, color=clr, edgecolor="#0a0a18", alpha=0.85)
                for patch, val in zip(patches, bins):
                    r = (val - bins.min()) / (bins.max() - bins.min() + 1e-9)
                    patch.set_facecolor(plt.cm.cool(r))
                ax.set_xlabel(cx)

            # ── BOX PLOT ────────────────────────────────────────────
            elif ct == "Box Plot":
                data = pd.to_numeric(df[cy], errors="coerce").dropna()
                ax.boxplot(data, patch_artist=True, notch=True,
                           boxprops=dict(facecolor=clr, color=clr2, alpha=0.7),
                           medianprops=dict(color="white", linewidth=2.5),
                           whiskerprops=dict(color="#aaaacc"),
                           capprops=dict(color="#aaaacc"),
                           flierprops=dict(marker="o", color=clr2, markersize=4, alpha=0.5))
                ax.set_ylabel(cy)

            # ── HEATMAP ─────────────────────────────────────────────
            elif ct == "Heatmap":
                num_data = df.select_dtypes(include="number")
                if num_data.shape[1] >= 2:
                    corr = num_data.corr()
                    mask = np.triu(np.ones_like(corr, dtype=bool))
                    sns.heatmap(corr, ax=ax, annot=True, fmt=".2f",
                                cmap="coolwarm", linewidths=0.4,
                                annot_kws={"size":7,"color":"white"},
                                cbar_kws={"shrink":0.75}, mask=mask)
                else:
                    ax.text(0.5,0.5,"Need ≥ 2 numeric columns",ha="center",va="center",
                            color="white",transform=ax.transAxes)

            # ── AREA CHART ──────────────────────────────────────────
            elif ct == "Area Chart":
                data = pd.to_numeric(df[cy], errors="coerce").dropna().reset_index(drop=True)
                ax.fill_between(range(len(data)), data, alpha=0.45, color=clr)
                ax.plot(data, color=clr, linewidth=2)
                ax.set_ylabel(cy)

            # ── STACKED AREA ─────────────────────────────────────────
            elif ct == "Stacked Area":
                cols = num_cols[:5]
                data = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0).reset_index(drop=True)
                colors_sa = sns.color_palette(palette, len(cols))
                ax.stackplot(range(len(data)), [data[c].values for c in cols],
                             labels=cols, colors=colors_sa, alpha=0.7)
                ax.legend(labelcolor="white", facecolor="#111128", edgecolor=BORDER, fontsize=8)

            # ── COUNT PLOT ──────────────────────────────────────────
            elif ct == "Count Plot":
                data = df[cx].value_counts().head(15)
                colors_cp = sns.color_palette(palette, len(data))
                bars = ax.barh(data.index.astype(str)[::-1], data.values[::-1],
                               color=colors_cp, alpha=0.9)
                if show_v:
                    for b in bars:
                        ax.text(b.get_width()+max(data.values)*0.01,
                                b.get_y()+b.get_height()/2,
                                f"{b.get_width():,.0f}", va="center", fontsize=8, color="white")
                ax.set_xlabel("Count")

            # ── VIOLIN PLOT ──────────────────────────────────────────
            elif ct == "Violin Plot":
                data = pd.to_numeric(df[cy], errors="coerce").dropna()
                parts = ax.violinplot(data, showmeans=True, showmedians=True)
                for pc in parts["bodies"]:
                    pc.set_facecolor(clr); pc.set_alpha(0.7)
                ax.set_ylabel(cy)

            # ── KDE PLOT ─────────────────────────────────────────────
            elif ct == "KDE Plot":
                data = pd.to_numeric(df[cx], errors="coerce").dropna()
                sns.kdeplot(data, ax=ax, color=clr, fill=True, alpha=0.5, linewidth=2)
                ax.set_xlabel(cx)

            # ── REGRESSION PLOT ──────────────────────────────────────
            elif ct == "Regression Plot":
                xd = pd.to_numeric(df[cx], errors="coerce")
                yd = pd.to_numeric(df[cy], errors="coerce")
                mask = xd.notna() & yd.notna()
                ax.scatter(xd[mask], yd[mask], alpha=0.4, c=clr, s=15, edgecolors="none")
                m, b_val = np.polyfit(xd[mask], yd[mask], 1)
                xline = np.linspace(xd[mask].min(), xd[mask].max(), 100)
                ax.plot(xline, m*xline+b_val, color=clr2, linewidth=2.5, label=f"y={m:.2f}x+{b_val:.2f}")
                ax.legend(labelcolor="white", facecolor="#111128", edgecolor=BORDER)
                ax.set_xlabel(cx); ax.set_ylabel(cy)

            # ── STEP CHART ───────────────────────────────────────────
            elif ct == "Step Chart":
                data = pd.to_numeric(df[cy], errors="coerce").dropna().reset_index(drop=True)
                ax.step(range(len(data)), data, color=clr, linewidth=2, alpha=0.9, where="mid")
                ax.fill_between(range(len(data)), data, step="mid", alpha=0.2, color=clr)

            # ── LOLLIPOP CHART ───────────────────────────────────────
            elif ct == "Lollipop Chart":
                data = (df.groupby(cx)[cy].sum().sort_values(ascending=False).head(15)
                        if cy in num_cols else df[cx].value_counts().head(15))
                x_pos = range(len(data))
                colors_lp = sns.color_palette(palette, len(data))
                ax.vlines(x_pos, 0, data.values, color=TEXT_DIM, linewidth=1.5, alpha=0.6)
                ax.scatter(x_pos, data.values, c=colors_lp, s=80, zorder=5)
                plt.xticks(list(x_pos), data.index.astype(str), rotation=45, ha="right")
                if show_v:
                    for i, v in enumerate(data.values):
                        ax.text(i, v+max(data.values)*0.01, f"{v:,.0f}", ha="center",
                                fontsize=8, color="white")

            # ── WATERFALL CHART ──────────────────────────────────────
            elif ct == "Waterfall Chart":
                data = (df.groupby(cx)[cy].sum().sort_values(ascending=False).head(12)
                        if cy in num_cols else df[cx].value_counts().head(12))
                running = 0
                for i, (label, val) in enumerate(data.items()):
                    color = SUCCESS if val >= 0 else ERROR
                    ax.bar(i, val, bottom=running, color=color, edgecolor="none", alpha=0.85)
                    if show_v:
                        ax.text(i, running+val+max(abs(data.values))*0.01, f"{val:,.0f}",
                                ha="center", fontsize=8, color="white")
                    running += val
                plt.xticks(range(len(data)), data.index.astype(str), rotation=45, ha="right")

            # ── ANIMATED BAR RACE ────────────────────────────────────
            elif ct == "Animated Bar Race":
                data = df[cx].value_counts().head(10)
                sorted_vals = sorted(data.values)
                colors_br = sns.color_palette(palette, len(data))
                bars_br = ax.barh(data.index.astype(str), [0]*len(data), color=colors_br)
                ax.set_xlim(0, max(data.values) * 1.15)

                def anim_race(frame):
                    progress = min(frame / 40, 1.0)
                    for bar_r, val in zip(bars_br, data.values):
                        bar_r.set_width(val * progress)
                    return bars_br

                ani = animation.FuncAnimation(fig, anim_race, frames=50,
                                               interval=50, repeat=False, blit=True)
                fig._anim = ani

            # ── ROLLING LINE ─────────────────────────────────────────
            elif ct == "Rolling Line":
                data = pd.to_numeric(df[cy], errors="coerce").dropna().reset_index(drop=True)
                rolled = data.rolling(window=7, min_periods=1).mean()
                ax.plot(data, color=clr, alpha=0.35, linewidth=1, label="Raw")
                ax.plot(rolled, color=clr2, linewidth=2.5, label="7-period MA")
                ax.fill_between(range(len(rolled)), rolled, alpha=0.2, color=clr2)
                ax.legend(labelcolor="white", facecolor="#111128", edgecolor=BORDER)
                ax.set_ylabel(cy)

            if log_sc:
                try:
                    ax.set_yscale("log")
                except:
                    pass

            ax.set_title(title, color=ACCENT, fontsize=13, pad=10, fontweight="bold")

        except Exception as e:
            ax.text(0.5, 0.5, f"Error: {e}\n\nCheck column types",
                    ha="center", va="center", color="#ff5555",
                    transform=ax.transAxes, fontsize=11)

        plt.tight_layout(pad=1.5)
        current_fig = fig
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, canvas_frame)
        toolbar.update()
        canvas.get_tk_widget().pack(fill="both", expand=True)

# ─────────────────────────────────────────────
#  7. AI INSIGHTS
# ─────────────────────────────────────────────
def ai_insights():
    if not check_df(): return
    clear_main()
    page_title("AI Insights Engine", "💡")

    result = ctk.CTkScrollableFrame(main_frame, fg_color=BG_CARD,
                                     corner_radius=10, height=580)
    result.pack(padx=20, pady=5, fill="both", expand=True)

    loading_lbl = ctk.CTkLabel(main_frame,
                                text="Click '💡 Generate Insights' to analyse your data",
                                font=("Segoe UI", 13), text_color=TEXT_DIM)
    loading_lbl.pack(pady=4)

    gen_btn = ctk.CTkButton(main_frame, text="💡  Generate Insights",
                             fg_color=ACCENT2, hover_color="#6d28d9",
                             font=("Segoe UI", 14, "bold"),
                             width=240, height=46, corner_radius=12)
    gen_btn.pack(pady=8)

    def add_card(text, color=TEXT_MAIN):
        f = ctk.CTkFrame(result, fg_color="#0f0f25", corner_radius=8,
                          border_width=1, border_color=BORDER)
        f.pack(fill="x", padx=10, pady=3)
        ctk.CTkLabel(f, text=text, font=("Segoe UI", 12),
                     text_color=color, wraplength=960,
                     justify="left").pack(padx=14, pady=8, anchor="w")

    def generate_insights():
        for w in result.winfo_children(): w.destroy()
        gen_btn.configure(state="disabled", text="⏳ Analysing...")

        insights = []
        insights.append(("━━━  DATASET OVERVIEW  ━━━", ACCENT))
        insights.append((f"   📐 {df.shape[0]:,} rows  ×  {df.shape[1]} columns", TEXT_MAIN))
        mem = df.memory_usage(deep=True).sum() / 1024
        insights.append((f"   💾 Memory usage: {mem:.1f} KB", TEXT_DIM))

        total_null = df.isnull().sum().sum()
        pct = round(total_null / df.size * 100, 1) if df.size > 0 else 0
        insights.append((f"   {'✅ No missing values' if total_null == 0 else f'⚠️ {total_null:,} missing ({pct}%)'}",
                         SUCCESS if total_null == 0 else WARNING))

        dup = df.duplicated().sum()
        insights.append((f"   {'✅ No duplicates' if dup == 0 else f'🔁 {dup:,} duplicates found'}",
                         SUCCESS if dup == 0 else ERROR))

        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            insights.append(("\n━━━  NUMERIC INSIGHTS  ━━━", ACCENT))
            for col in num_df.columns[:10]:
                vals = num_df[col].dropna()
                if len(vals) == 0: continue
                mean_v = round(float(vals.mean()), 2)
                std_v  = round(float(vals.std()), 2)
                skew_v = round(float(vals.skew()), 2)
                Q1  = vals.quantile(0.25)
                Q3  = vals.quantile(0.75)
                IQR = Q3 - Q1
                outliers = int(((vals < Q1-1.5*IQR) | (vals > Q3+1.5*IQR)).sum())
                flags = []
                if abs(skew_v) > 1: flags.append("skewed")
                if outliers > len(vals)*0.05: flags.append(f"{outliers} outliers")
                flag_str = "  ⚠️ "+", ".join(flags) if flags else ""
                insights.append((f"   • {col:<28}  mean={mean_v:>10,}  std={std_v:>10,}{flag_str}",
                                  WARNING if flags else TEXT_MAIN))

        cat_df = df.select_dtypes(include="object")
        if not cat_df.empty:
            insights.append(("\n━━━  CATEGORICAL INSIGHTS  ━━━", ACCENT))
            for col in cat_df.columns[:8]:
                unique = df[col].nunique()
                top = df[col].value_counts().index[0] if unique > 0 else "N/A"
                top_pct = round(df[col].value_counts().iloc[0] / len(df) * 100, 1) if unique > 0 else 0
                insights.append((f"   • {col:<28}  {unique} unique  |  Top: '{top}' ({top_pct}%)", TEXT_MAIN))

        if not num_df.empty and num_df.shape[1] >= 2:
            insights.append(("\n━━━  CORRELATIONS  ━━━", ACCENT))
            corr = num_df.corr().abs()
            pairs = []
            cols_c = corr.columns.tolist()
            for i in range(len(cols_c)):
                for j in range(i+1, len(cols_c)):
                    pairs.append((cols_c[i], cols_c[j], round(corr.iloc[i,j], 3)))
            pairs.sort(key=lambda x: x[2], reverse=True)
            for a, b, c_val in pairs[:5]:
                strength = "🔴 STRONG" if c_val > 0.7 else ("🟡 MODERATE" if c_val > 0.4 else "🟢 WEAK")
                insights.append((f"   • {a} ↔ {b}  :  {c_val}  {strength}",
                                  ERROR if c_val > 0.7 else (WARNING if c_val > 0.4 else SUCCESS)))

        if "Profit" in df.columns:
            p = pd.to_numeric(df["Profit"], errors="coerce")
            insights.append(("\n━━━  PROFIT ANALYSIS  ━━━", ACCENT))
            insights.append((f"   💰 Total Profit    : {round(p.sum(),2):,}", SUCCESS if p.sum() > 0 else ERROR))
            insights.append((f"   📊 Avg Profit      : {round(p.mean(),2):,}", TEXT_MAIN))
            insights.append((f"   ❌ Loss Orders     : {(p<0).sum():,}", ERROR if (p<0).sum() > 0 else SUCCESS))
            insights.append((f"   ✅ Profit Orders   : {(p>0).sum():,}", SUCCESS))

        if "Sales" in df.columns:
            s = pd.to_numeric(df["Sales"], errors="coerce")
            insights.append(("\n━━━  SALES ANALYSIS  ━━━", ACCENT))
            insights.append((f"   💵 Total Sales     : {round(s.sum(),2):,}", ACCENT))
            insights.append((f"   📊 Avg Sale        : {round(s.mean(),2):,}", TEXT_MAIN))
            insights.append((f"   📈 Max Sale        : {round(s.max(),2):,}", SUCCESS))
            insights.append((f"   📉 Min Sale        : {round(s.min(),2):,}", WARNING))

        for text, color in insights:
            add_card(text, color)

        gen_btn.configure(state="normal", text="💡  Generate Insights")
        show_toast("✅ Insights generated!")

    def threaded_insights():
        run_in_thread(generate_insights)

    gen_btn.configure(command=threaded_insights)

# ─────────────────────────────────────────────
#  8. AI CHATBOT  (Gemini AI)
# ─────────────────────────────────────────────
def ai_chatbot():
    if not check_df(): return
    clear_main()
    page_title("AI Chatbot  (Powered by Google Gemini)", "🤖")

    # API Key frame
    api_frame = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                              corner_radius=10, border_width=1, border_color=BORDER)
    api_frame.pack(fill="x", padx=20, pady=5)

    ctk.CTkLabel(api_frame, text="🔑  Gemini API Key:",
                 font=("Segoe UI", 12, "bold"),
                 text_color=ACCENT2).pack(side="left", padx=12, pady=10)

    api_key_var = ctk.StringVar()
    api_entry = ctk.CTkEntry(api_frame,
                              textvariable=api_key_var,
                              width=380, height=34,
                              font=("Segoe UI", 11),
                              show="*",
                              placeholder_text="AIza... (get from aistudio.google.com)",
                              fg_color="#1a1a3a")
    api_entry.pack(side="left", padx=6)
    ctk.CTkButton(api_frame, text="Show/Hide",
                  width=90, height=30,
                  fg_color="#1a1a3a", hover_color=ACCENT2,
                  font=("Segoe UI", 10),
                  command=lambda: api_entry.configure(
                      show="" if api_entry.cget("show") == "*" else "*")
                  ).pack(side="left", padx=4)

    use_gemini_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(api_frame, text="Use Gemini AI",
                    variable=use_gemini_var,
                    checkbox_width=20, checkbox_height=20,
                    fg_color=SUCCESS,
                    font=("Segoe UI", 11),
                    text_color=TEXT_MAIN).pack(side="left", padx=12)

    model_var = ctk.StringVar(value="gemini-2.0-flash")
    ctk.CTkComboBox(api_frame,
                    values=["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
                    variable=model_var, width=180, height=30,
                    font=("Segoe UI", 10), fg_color="#1a1a3a",
                    button_color=ACCENT2).pack(side="left", padx=6)

    chat_box = ctk.CTkScrollableFrame(main_frame, fg_color=BG_CARD,
                                       corner_radius=10, height=420)
    chat_box.pack(padx=20, pady=5, fill="both", expand=True)

    input_frame = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                                corner_radius=10, border_width=1, border_color=BORDER)
    input_frame.pack(fill="x", padx=20, pady=8)

    entry = ctk.CTkEntry(input_frame,
                          placeholder_text="Ask anything about your data...",
                          width=720, height=44,
                          font=("Segoe UI", 13),
                          fg_color="#1a1a3a")
    entry.pack(side="left", padx=12, pady=8)

    def add_bubble(text, is_user=True):
        align  = "e" if is_user else "w"
        bg     = ACCENT2 if is_user else "#0a1a2a"
        prefix = "👤" if is_user else "✨"
        outer = ctk.CTkFrame(chat_box, fg_color="transparent")
        outer.pack(anchor=align, pady=3, padx=12, fill="x")
        f = ctk.CTkFrame(outer, fg_color=bg, corner_radius=14)
        f.pack(anchor=align)
        ctk.CTkLabel(f, text=f"{prefix}  {text}",
                     font=("Segoe UI", 12),
                     wraplength=740, justify="left",
                     text_color="white").pack(padx=14, pady=10, anchor="w")
        try:
            chat_box._parent_canvas.yview_moveto(1.0)
        except:
            pass

    def get_df_context():
        if df is None:
            return "No dataset loaded."
        context  = f"Dataset Info:\n"
        context += f"  Shape: {df.shape[0]:,} rows × {df.shape[1]} cols\n"
        context += f"  Columns: {', '.join(df.columns.tolist())}\n"
        context += f"  Dtypes: {df.dtypes.to_dict()}\n"
        context += f"  Nulls: {df.isnull().sum().sum()}\n"
        context += f"  Duplicates: {df.duplicated().sum()}\n"
        num_df = df.select_dtypes(include="number")
        if not num_df.empty:
            context += "Numeric Stats:\n"
            for col in num_df.columns[:10]:
                context += (f"  {col}: mean={round(float(num_df[col].mean()),2)}, "
                            f"min={round(float(num_df[col].min()),2)}, "
                            f"max={round(float(num_df[col].max()),2)}, "
                            f"null={num_df[col].isnull().sum()}\n")
        if "Profit" in df.columns:
            p = pd.to_numeric(df["Profit"], errors="coerce")
            context += f"Profit Summary: total={round(p.sum(),2)}, avg={round(p.mean(),2)}, loss_orders={(p<0).sum()}\n"
        if "Sales" in df.columns:
            s = pd.to_numeric(df["Sales"], errors="coerce")
            context += f"Sales Summary: total={round(s.sum(),2)}, avg={round(s.mean(),2)}, max={round(s.max(),2)}\n"
        for col in df.select_dtypes("object").columns[:6]:
            context += f"  {col} top values: {', '.join(df[col].value_counts().head(3).index.tolist())}\n"
        return context

    def get_local_response(msg):
        msg_lower = msg.lower()
        if df is None:
            return "Please upload a dataset first!"
        if any(w in msg_lower for w in ["row","size","shape","how many"]):
            return f"The dataset has {df.shape[0]:,} rows and {df.shape[1]} columns."
        if "column" in msg_lower:
            return f"Columns ({df.shape[1]}):\n{', '.join(df.columns.tolist())}"
        if "missing" in msg_lower or "null" in msg_lower:
            n = df.isnull().sum().sum()
            if n == 0: return "✅ No missing values!"
            details = df.isnull().sum()
            return "Missing values:\n" + "\n".join(f"  {c}: {v}" for c,v in details.items() if v>0)
        if "duplicate" in msg_lower:
            return f"Duplicate rows: {df.duplicated().sum():,}"
        if "mean" in msg_lower or "average" in msg_lower:
            num = df.select_dtypes(include="number")
            if not num.empty:
                return "\n".join([f"  {c}: {round(float(num[c].mean()),2):,}" for c in num.columns])
        if "max" in msg_lower:
            num = df.select_dtypes(include="number")
            if not num.empty:
                return "\n".join([f"  {c}: {round(float(num[c].max()),2):,}" for c in num.columns])
        if "min" in msg_lower:
            num = df.select_dtypes(include="number")
            if not num.empty:
                return "\n".join([f"  {c}: {round(float(num[c].min()),2):,}" for c in num.columns])
        if "profit" in msg_lower and "Profit" in df.columns:
            p = pd.to_numeric(df["Profit"], errors="coerce")
            return (f"Total Profit: {round(p.sum(),2):,}\n"
                    f"Avg Profit: {round(p.mean(),2):,}\n"
                    f"Loss orders: {(p<0).sum():,}")
        if "sales" in msg_lower and "Sales" in df.columns:
            s = pd.to_numeric(df["Sales"], errors="coerce")
            return (f"Total Sales: {round(s.sum(),2):,}\n"
                    f"Avg Sale: {round(s.mean(),2):,}\n"
                    f"Max Sale: {round(s.max(),2):,}")
        if "category" in msg_lower and "Category" in df.columns:
            return f"Categories:\n{', '.join(df['Category'].unique())}"
        if "region" in msg_lower and "Region" in df.columns:
            return f"Regions:\n{', '.join(df['Region'].unique())}"
        if "top" in msg_lower and "product" in msg_lower:
            if "Product Name" in df.columns and "Sales" in df.columns:
                top = df.groupby("Product Name")["Sales"].sum().sort_values(ascending=False).head(5)
                return "Top 5 Products by Sales:\n" + "\n".join([f"  {k}: {round(v,2):,}" for k,v in top.items()])
        if any(w in msg_lower for w in ["hello","hi","hey","how are"]):
            return "Hello! 👋 I'm your data assistant. Ask me anything about your dataset!\n\nTip: Enable Gemini AI above for smarter, context-aware answers!"
        if "help" in msg_lower:
            return ("I can answer:\n"
                    "• rows / columns / shape / size\n"
                    "• missing values / duplicates\n"
                    "• mean / max / min / sum\n"
                    "• profit / sales summary\n"
                    "• top products\n"
                    "• category / region info\n\n"
                    "💡 Enable Gemini AI for smarter answers!")
        return ("Not sure — try:\n"
                "  'how many rows?'\n"
                "  'profit summary?'\n"
                "  'average sales?'\n"
                "  'list columns?'\n"
                "Or enable Gemini AI for smart answers! ✨")

    def call_gemini_api(user_msg):
        """Call Google Gemini API"""
        key = api_key_var.get().strip()
        if not key:
            return None, "API key not set. Enter your Gemini API key above."

        ctx = get_df_context()
        system_context = (
            "You are an expert data analyst assistant. "
            f"Current dataset context:\n{ctx}\n"
            "Answer questions about this data concisely and clearly. "
            "Use numbers and statistics from the context when answering. "
            "Be specific and helpful."
        )

        model = model_var.get()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        payload = json.dumps({
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_context}\n\nUser question: {user_msg}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
                "topP": 0.9,
            }
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data_r = json.loads(resp.read().decode("utf-8"))
                text = data_r["candidates"][0]["content"]["parts"][0]["text"]
                return text, None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            try:
                err = json.loads(body)
                msg_err = err.get("error", {}).get("message", "Unknown error")
                return None, f"Gemini API Error: {msg_err}"
            except:
                return None, f"HTTP {e.code}: {body[:300]}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def send():
        msg = entry.get().strip()
        if not msg: return
        add_bubble(msg, is_user=True)
        chat_history.append({"role": "user", "content": msg})
        entry.delete(0, "end")
        send_btn.configure(state="disabled", text="⏳")

        def process():
            if use_gemini_var.get():
                resp, err = call_gemini_api(msg)
                if err:
                    response = f"⚠️ {err}\n\nFallback answer:\n{get_local_response(msg)}"
                else:
                    response = resp
            else:
                response = get_local_response(msg)
            chat_history.append({"role": "assistant", "content": response})
            app.after(0, lambda: add_bubble(response, is_user=False))
            app.after(0, lambda: send_btn.configure(state="normal", text="Send ➤"))

        run_in_thread(process)

    def clear_chat():
        for w in chat_box.winfo_children(): w.destroy()
        chat_history.clear()
        add_bubble("Chat cleared. 🗑️ Ask me anything about your data!", is_user=False)

    entry.bind("<Return>", lambda e: send())
    send_btn = ctk.CTkButton(input_frame, text="Send ➤",
                              command=send,
                              fg_color=ACCENT2, hover_color="#6d28d9",
                              font=("Segoe UI", 13, "bold"),
                              width=110, height=44, corner_radius=8)
    send_btn.pack(side="left", padx=6)

    ctk.CTkButton(input_frame, text="🗑️ Clear",
                  command=clear_chat,
                  fg_color="#1a0a0a", hover_color=ERROR,
                  font=("Segoe UI", 12),
                  width=80, height=44, corner_radius=8).pack(side="left", padx=4)

    add_bubble("Hello! 👋 I'm your Gemini AI-powered data analyst.\n\n• Enable 'Use Gemini AI' + enter your API key for smart answers\n• Or ask basic questions without API key\n• Type 'help' for example questions", is_user=False)

# ─────────────────────────────────────────────
#  9. EXPORT  (Enhanced)
# ─────────────────────────────────────────────
def export_data():
    if not check_df(): return
    clear_main()
    page_title("Export Data", "💾")

    ctk.CTkLabel(main_frame,
                 text=f"Current dataset:  {df.shape[0]:,} rows  ×  {df.shape[1]} columns",
                 font=("Segoe UI", 13), text_color=TEXT_DIM).pack(pady=5)

    # Export Options
    opts_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                           corner_radius=10, border_width=1, border_color=BORDER)
    opts_f.pack(fill="x", padx=20, pady=6)
    opts_row = ctk.CTkFrame(opts_f, fg_color="transparent")
    opts_row.pack(fill="x", padx=15, pady=10)
    incl_idx_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(opts_row, text="Include Index",
                    variable=incl_idx_var,
                    font=("Segoe UI", 11), text_color=TEXT_MAIN,
                    fg_color=ACCENT2).pack(side="left", padx=10)

    btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    btn_frame.pack(pady=20)

    def export_csv():
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV File","*.csv")])
        if path:
            df.to_csv(path, index=incl_idx_var.get())
            show_toast("✅ Exported CSV!")

    def export_excel():
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel File","*.xlsx")])
        if path:
            df.to_excel(path, index=incl_idx_var.get())
            show_toast("✅ Exported Excel!")

    def export_json():
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                             filetypes=[("JSON File","*.json")])
        if path:
            df.to_json(path, orient="records", indent=2)
            show_toast("✅ Exported JSON!")

    def export_markdown():
        path = filedialog.asksaveasfilename(defaultextension=".md",
                                             filetypes=[("Markdown","*.md")])
        if path:
            with open(path, "w") as f_out:
                f_out.write(f"# Data Export\n\n")
                f_out.write(f"**Rows:** {df.shape[0]:,}  |  **Columns:** {df.shape[1]}\n\n")
                f_out.write(df.head(100).to_markdown(index=False))
            show_toast("✅ Exported Markdown!")

    def export_html():
        path = filedialog.asksaveasfilename(defaultextension=".html",
                                             filetypes=[("HTML","*.html")])
        if path:
            html_str = df.head(500).to_html(index=incl_idx_var.get(), classes="data-table", border=0)
            styled = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>SMU AI Export</title><style>
body{{font-family:Segoe UI,sans-serif;background:#0a0a14;color:#d0d8ff;padding:20px}}
.data-table{{border-collapse:collapse;width:100%}}
.data-table th{{background:#7c3aed;color:#fff;padding:8px 12px;text-align:left}}
.data-table td{{padding:6px 12px;border-bottom:1px solid #1a1a3a}}
.data-table tr:hover{{background:#111128}}
h1{{color:#00d4ff}}
</style></head><body>
<h1>📊 SMU AI Dashboard Export</h1>
<p>Rows: {df.shape[0]:,} | Columns: {df.shape[1]}</p>
{html_str}</body></html>"""
            with open(path, "w", encoding="utf-8") as f_out:
                f_out.write(styled)
            show_toast("✅ Exported HTML!")

    def export_stats():
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV","*.csv")])
        if path:
            stats = df.describe(include="all").T
            stats.to_csv(path)
            show_toast("✅ Exported Stats Summary!")

    export_buttons = [
        ("📄  Export as CSV",     export_csv,    "#0a2a0a"),
        ("📊  Export as Excel",   export_excel,  "#0a0a2a"),
        ("🗂️   Export as JSON",    export_json,   "#1a0a0a"),
        ("🌐  Export as HTML",     export_html,   "#0a1a2a"),
        ("📝  Export as Markdown", export_markdown,"#1a1a0a"),
        ("📈  Export Stats CSV",   export_stats,  "#1a0a1a"),
    ]

    for i, (text, cmd, color) in enumerate(export_buttons):
        row = i // 3
        col = i % 3
        if col == 0:
            row_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
            row_frame.pack(pady=5)
        ctk.CTkButton(row_frame, text=text, command=cmd,
                      fg_color=color, hover_color=ACCENT2,
                      font=("Segoe UI", 13, "bold"),
                      width=260, height=54, corner_radius=12).pack(side="left", padx=8)

# ─────────────────────────────────────────────
#  10. DATA FILTER (New!)
# ─────────────────────────────────────────────
def data_filter():
    global df
    if not check_df(): return
    clear_main()
    page_title("Data Filter & Query", "🔍")

    query_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                            corner_radius=10, border_width=1, border_color=BORDER)
    query_f.pack(fill="x", padx=20, pady=6)
    ctk.CTkLabel(query_f, text="Pandas Query Expression:",
                 font=("Segoe UI", 12), text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(10,4))

    q_row = ctk.CTkFrame(query_f, fg_color="transparent")
    q_row.pack(fill="x", padx=15, pady=(0,10))
    query_entry = ctk.CTkEntry(q_row,
                                placeholder_text="e.g.  Sales > 500  or  Region == 'West'",
                                height=38, font=("Segoe UI", 12), fg_color="#1a1a3a")
    query_entry.pack(side="left", fill="x", expand=True, padx=(0,8))

    result_lbl = ctk.CTkLabel(query_f, text="",
                               font=("Segoe UI", 12), text_color=TEXT_DIM)
    result_lbl.pack(anchor="w", padx=15, pady=(0,8))

    tbl_frame = ctk.CTkScrollableFrame(main_frame, fg_color=BG_CARD,
                                        corner_radius=10, height=480)
    tbl_frame.pack(fill="both", expand=True, padx=20, pady=6)

    filtered_df = [df.copy()]

    def run_filter():
        global df
        q = query_entry.get().strip()
        if not q:
            show_toast("⚠️ Enter a query expression", WARNING); return
        try:
            result = df.query(q)
            filtered_df[0] = result
            result_lbl.configure(text=f"✅  {len(result):,} rows matched  ({round(len(result)/len(df)*100,1)}%)",
                                  text_color=SUCCESS)
            for w in tbl_frame.winfo_children(): w.destroy()
            headers = list(result.columns[:10])
            for c_idx, col in enumerate(headers):
                ctk.CTkLabel(tbl_frame, text=col, font=("Segoe UI", 10, "bold"),
                             width=120, fg_color=ACCENT2, text_color="white",
                             corner_radius=5).grid(row=0, column=c_idx, padx=2, pady=2, sticky="ew")
            for r, (_, row) in enumerate(result.head(50).iterrows(), start=1):
                bg = BG_CARD if r % 2 == 0 else "#101025"
                for c_idx, col in enumerate(headers):
                    val = str(row[col])[:18]
                    ctk.CTkLabel(tbl_frame, text=val, font=("Consolas", 10),
                                 width=120, fg_color=bg, text_color=TEXT_MAIN,
                                 corner_radius=3).grid(row=r, column=c_idx, padx=2, pady=1, sticky="ew")
        except Exception as e:
            result_lbl.configure(text=f"❌ Error: {e}", text_color=ERROR)
            show_toast(f"❌ Query error: {e}", ERROR)

    def apply_filter():
        global df
        if filtered_df[0] is not None and len(filtered_df[0]) > 0:
            df = filtered_df[0].copy()
            show_toast(f"✅ Filter applied! {len(df):,} rows remaining")

    ctk.CTkButton(q_row, text="🔍 Filter",
                  command=run_filter,
                  fg_color=ACCENT2, hover_color="#6d28d9",
                  font=("Segoe UI", 12, "bold"),
                  width=120, height=38, corner_radius=8).pack(side="left", padx=4)

    ctk.CTkButton(q_row, text="✅ Apply",
                  command=apply_filter,
                  fg_color=SUCCESS, hover_color="#065f46",
                  font=("Segoe UI", 12, "bold"),
                  width=100, height=38, corner_radius=8).pack(side="left", padx=4)

    # Quick filter examples
    examples_f = ctk.CTkFrame(main_frame, fg_color=BG_CARD,
                               corner_radius=10, border_width=1, border_color=BORDER)
    examples_f.pack(fill="x", padx=20, pady=4)
    ctk.CTkLabel(examples_f, text="Quick Examples:",
                 font=("Segoe UI", 11), text_color=TEXT_DIM).pack(side="left", padx=10, pady=8)

    num_cols_df = df.select_dtypes(include="number").columns.tolist()
    examples = []
    if num_cols_df:
        col = num_cols_df[0]
        median_val = round(float(df[col].median()), 2)
        examples.append(f"{col} > {median_val}")
        examples.append(f"{col} == {df[col].max()}")

    for ex in examples[:3]:
        ctk.CTkButton(examples_f, text=ex,
                      command=lambda e=ex: query_entry.delete(0,"end") or query_entry.insert(0,e),
                      fg_color="#1a1a3a", hover_color=ACCENT2,
                      font=("Segoe UI", 10), height=28, corner_radius=6
                      ).pack(side="left", padx=4)

# ─────────────────────────────────────────────
#  11. CHANGE BACKGROUND
# ─────────────────────────────────────────────
def change_bg():
    path = filedialog.askopenfilename(
        filetypes=[("Image Files","*.png *.jpg *.jpeg *.webp")]
    )
    if not path: return
    try:
        img    = Image.open(path).resize((1600, 950))
        bg_img = ctk.CTkImage(light_image=img, dark_image=img, size=(1600, 950))
        bg_label.configure(image=bg_img)
        bg_label.image = bg_img
        show_toast("✅ Background changed!")
    except Exception as e:
        messagebox.showerror("Error", f"❌ {e}")

def change_icon():
    path = filedialog.askopenfilename(
        filetypes=[("ICO Files","*.ico"),("PNG Files","*.png")]
    )
    if not path: return
    try:
        app.iconbitmap(path)
        show_toast("✅ Icon changed!")
    except Exception as e:
        messagebox.showerror("Error", f"❌ {e}")

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
brand_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
brand_frame.pack(pady=(18,4), padx=10, fill="x")
ctk.CTkLabel(brand_frame, text="◈ SMU AI Pro",
             font=("Segoe UI", 18, "bold"),
             text_color=ACCENT).pack()
ctk.CTkLabel(brand_frame, text="Advanced Data Dashboard",
             font=("Segoe UI", 9),
             text_color=TEXT_DIM).pack()

ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=(8,10))
ctk.CTkLabel(sidebar, text="MODULES",
             font=("Segoe UI", 9, "bold"),
             text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(0,4))

sidebar_buttons = []

module_buttons = [
    ("📤   Upload Data",           upload_data),
    ("🧹   Data Cleaning",         clean_data),
    ("⚙️    Processing",            process_data),
    ("📊   EDA",                   eda),
    ("🔧   Feature Engineering",   feature_engineering),
    ("📈   Visualization",         visualize),
    ("🔍   Filter & Query",        data_filter),
    ("💡   AI Insights",           ai_insights),
    ("🤖   AI Chatbot (Gemini)",   ai_chatbot),
    ("💾   Export",                export_data),
]

for text, cmd in module_buttons:
    btn = ctk.CTkButton(sidebar, text=text,
                        fg_color="#0f0f22",
                        hover_color=ACCENT2,
                        font=("Segoe UI", 11),
                        anchor="w",
                        width=198, height=36,
                        corner_radius=8)

    def make_cmd(c, b):
        def fn():
            set_active_btn(b)
            c()
        return fn

    btn.configure(command=make_cmd(cmd, btn))
    btn.pack(fill="x", padx=10, pady=2)
    sidebar_buttons.append(btn)

ctk.CTkLabel(sidebar, text="").pack(expand=True)

ctk.CTkFrame(sidebar, height=1, fg_color=BORDER).pack(fill="x", padx=10, pady=8)
ctk.CTkLabel(sidebar, text="CUSTOMISE",
             font=("Segoe UI", 9, "bold"),
             text_color=TEXT_DIM).pack(anchor="w", padx=15, pady=(0,4))

for text, cmd in [("🎨  Change BG", change_bg), ("🖼️   Change Icon", change_icon)]:
    ctk.CTkButton(sidebar, text=text, command=cmd,
                  fg_color="#0d0d20", hover_color="#1a1a3a",
                  font=("Segoe UI", 10), width=198, height=32,
                  corner_radius=8).pack(fill="x", padx=10, pady=2)

ctk.CTkLabel(sidebar, text="v3.0  ✦  SMU AI Pro",
             font=("Segoe UI", 9),
             text_color=TEXT_DIM).pack(pady=(8,12))

# ─────────────────────────────────────────────
#  WELCOME SCREEN
# ─────────────────────────────────────────────
welcome = ctk.CTkFrame(main_frame, fg_color="transparent")
welcome.pack(expand=True)

ctk.CTkLabel(welcome, text="◈",
             font=("Segoe UI", 64),
             text_color=ACCENT).pack(pady=(30,0))

ctk.CTkLabel(welcome, text="SMU AI Dashboard Pro",
             font=("Segoe UI", 38, "bold"),
             text_color=TEXT_MAIN).pack(pady=6)

ctk.CTkLabel(welcome, text="Advanced Analytics  ·  AI Insights  ·  Gemini Chatbot",
             font=("Segoe UI", 14),
             text_color=TEXT_DIM).pack()

ctk.CTkButton(welcome, text="📤   Upload Data to Begin",
              command=upload_data,
              fg_color=ACCENT2, hover_color="#6d28d9",
              font=("Segoe UI", 15, "bold"),
              width=260, height=54,
              corner_radius=14).pack(pady=28)

features_list = [
    "✦  Upload CSV / Excel / JSON",
    "✦  Smart Data Cleaning with Options",
    "✦  Advanced EDA + Correlation Analysis",
    "✦  23+ Chart Types with Animations",
    "✦  Feature Engineering + Custom Formulas",
    "✦  Data Filter & Query Engine",
    "✦  AI Insights Engine",
    "✦  Google Gemini AI Chatbot",
    "✦  Export: CSV / Excel / JSON / HTML / Markdown",
]

feat_f = ctk.CTkFrame(welcome, fg_color="transparent")
feat_f.pack(pady=4)
mid = len(features_list) // 2
for i, f in enumerate(features_list):
    side = "left" if i < mid + 1 else "right"
    col = i % 2
    ctk.CTkLabel(feat_f, text=f,
                 font=("Segoe UI", 11),
                 text_color=TEXT_DIM).grid(row=i//2, column=col, padx=20, pady=2, sticky="w")

# ─────────────────────────────────────────────
app.mainloop()
