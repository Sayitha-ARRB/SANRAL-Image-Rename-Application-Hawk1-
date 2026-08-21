import os
import shutil
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from decimal import Decimal, ROUND_CEILING

# ----------------- Helper functions -----------------

def extract_road_name(filename: str) -> str:
    parts = filename.replace('-', ' ').replace('_', ' ').split()

    for p in parts:
        if any(c.isalpha() for c in p) and any(c.isdigit() for c in p):
            return p

    return "UNKNOWN"


def format_chainage_6digit(chainage_km) -> str:
    # Rounds UP to nearest 10m
    value = Decimal(str(chainage_km))
    meters = value * Decimal("1000")

    rounded = (meters / Decimal("10")).to_integral_value(
        rounding=ROUND_CEILING
    ) * Decimal("10")

    return f"{int(rounded):06d}"


def get_direction_code(direction: str) -> str:
    # Converts survey direction into required naming convention
    d = str(direction).strip().upper()

    if d == "FORWARD":
        return "P1"

    elif d == "REVERSE":
        return "S1"

    return ""


def find_file_partial_match(folder, filename):
    def normalize(s):
        return os.path.splitext(s)[0].lower().replace(" ", "").replace("_", "")

    target = normalize(filename)

    for root, _, files in os.walk(folder):
        for f in files:
            if normalize(f).startswith(target):
                return os.path.join(root, f)

    return None


# ------------------ Core Function ------------------

def rename_images(csv_path, image_folder, output_folder):
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read CSV file:\n{e}")
        return

    df.columns = [c.strip() for c in df.columns]

    required_cols = [
        "Survey_Direction",
        "Chainage__km_",
        "Image_Filename"
    ]

    for col in required_cols:
        if col not in df.columns:
            messagebox.showerror("Error", f"Missing column: {col}")
            return

    # Ensure chainage is numeric
    df["Chainage__km_"] = pd.to_numeric(
        df["Chainage__km_"],
        errors="coerce"
    )

    renamed_count = 0
    missing_files = []
    skipped_invalid = []
    log_renames = []

    # ---------------- Processing loop ----------------

    for _, row in df.iterrows():
        try:
            original_name = str(row["Image_Filename"]).strip()
            survey_direction = str(row["Survey_Direction"]).strip().upper()
            chainage_km = row["Chainage__km_"]
        except Exception:
            skipped_invalid.append(
                str(row.get("Image_Filename", "UNKNOWN"))
            )
            continue

        # Skip invalid chainage
        if pd.isna(chainage_km):
            skipped_invalid.append(original_name)
            continue

        # Extract road name
        road_name = extract_road_name(original_name)

        # Get direction code
        direction_code = get_direction_code(survey_direction)

        if direction_code == "":
            skipped_invalid.append(original_name)
            continue

        # Format chainage
        chainage_str = format_chainage_6digit(chainage_km)

        # Find original image
        original_path = find_file_partial_match(
            image_folder,
            original_name
        )

        if not original_path:
            missing_files.append(original_name)
            continue

        # -------------- Filename format --------------
        # ROAD_NAME + P1/S1 + "_" + CHAINAGE


        new_filename = f"{road_name}{direction_code}_{chainage_str}.jpg"
        new_path = os.path.join(output_folder, new_filename)

        try:
            shutil.copy2(original_path, new_path)
            renamed_count += 1
            log_renames.append(
                f"{original_name} -> {new_filename}"
            )
        except Exception:
            continue

    # ---------------- Save rename log ----------------

    log_file_path = os.path.join(
        output_folder,
        "rename_log.txt"
    )

    try:
        with open(log_file_path, "w") as f:
            f.write("\n".join(log_renames))
    except Exception:
        pass

    # ---------------- Completion message ----------------

    msg = f"Renamed: {renamed_count} files"

    if missing_files:
        msg += f"\nMissing images: {len(missing_files)}"

    if skipped_invalid:
        msg += f"\nSkipped (invalid data): {len(skipped_invalid)}"

    msg += f"\nLog saved to: {log_file_path}"

    messagebox.showinfo("Done", msg)


# ----------------------- GUI ------------------------

class RenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PaveVision: WCG Image Rename (Hawk1)")
        self.root.geometry("640x360")
        self.root.resizable(False, False)

        self.csv_path = ""
        self.image_folder = ""
        self.output_folder = ""

        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        btn_opts = {"width": 40, "height": 2}
        lbl_opts = {"anchor": "w", "justify": "left", "wraplength": 580}

        tk.Button(frame, text="Select CSV File", command=self.select_csv, **btn_opts).pack(pady=(0,4))
        self.csv_label = tk.Label(frame, text="No CSV selected", fg="gray", **lbl_opts)
        self.csv_label.pack(fill="x", pady=(0,10))

        tk.Button(frame, text="Select Image Folder", command=self.select_images, **btn_opts).pack(pady=(0,4))
        self.img_label = tk.Label(frame, text="No image folder selected", fg="gray", **lbl_opts)
        self.img_label.pack(fill="x", pady=(0,10))

        tk.Button(frame, text="Select Output Folder", command=self.select_output, **btn_opts).pack(pady=(0,4))
        self.out_label = tk.Label(frame, text="No output folder selected", fg="gray", **lbl_opts)
        self.out_label.pack(fill="x", pady=(0,16))

        tk.Button(frame, text="Run Renaming", command=self.run, width=40, height=2, bg="#4CAF50", fg="white").pack()

    def select_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if path:
            self.csv_path = path
            self.csv_label.config(text=path, fg="black")

    def select_images(self):
        path = filedialog.askdirectory()
        if path:
            self.image_folder = path
            self.img_label.config(text=path, fg="black")

    def select_output(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder = path
            self.out_label.config(text=path, fg="black")

    def run(self):
        if not all([self.csv_path, self.image_folder, self.output_folder]):
            messagebox.showerror("Error", "Please select all inputs.")
            return
        rename_images(self.csv_path, self.image_folder, self.output_folder)        

# ----------------------- Run ------------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = RenamerApp(root)
    root.mainloop()
