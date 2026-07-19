#!/usr/bin/env python3
import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading

class CapCutSyncGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CapCut Timeline Sync Tool")
        self.root.geometry("880x650")
        self.root.minsize(750, 550)

        # Style configurations
        self.style = ttk.Style()
        self.style.theme_use('vista' if 'vista' in self.style.theme_names() else 'clam')
        
        # Main Frame
        main_frame = ttk.Frame(root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title Label
        title_label = ttk.Label(main_frame, text="CapCut Timeline Sync Tool", font=("Segoe UI", 16, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 15))

        # Top Inputs Frame (Drafts Dir & Timestamps)
        inputs_frame = ttk.LabelFrame(main_frame, text=" Đường dẫn hệ thống ", padding="10")
        inputs_frame.pack(fill=tk.X, pady=(0, 15))

        # Drafts Dir
        ttk.Label(inputs_frame, text="Thư mục Drafts CapCut:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.drafts_dir_var = tk.StringVar(value=self.get_default_drafts_dir())
        self.drafts_dir_entry = ttk.Entry(inputs_frame, textvariable=self.drafts_dir_var, width=60)
        self.drafts_dir_entry.grid(row=0, column=1, padx=(5, 5), sticky=tk.EW, pady=5)
        ttk.Button(inputs_frame, text="Browse...", command=self.browse_drafts_dir).grid(row=0, column=2, pady=5)

        # Timestamps File (TXT/JSON)
        ttk.Label(inputs_frame, text="File Timestamps (TXT/JSON):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.timestamps_var = tk.StringVar()
        self.timestamps_entry = ttk.Entry(inputs_frame, textvariable=self.timestamps_var, width=60)
        self.timestamps_entry.grid(row=1, column=1, padx=(5, 5), sticky=tk.EW, pady=5)
        ttk.Button(inputs_frame, text="Browse...", command=self.browse_timestamps).grid(row=1, column=2, pady=5)

        inputs_frame.columnconfigure(1, weight=1)

        # Middle Split: Options (Left) and Projects List (Right)
        split_frame = ttk.Frame(main_frame)
        split_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Left Pane: Options & Action
        left_pane = ttk.LabelFrame(split_frame, text=" Tùy chọn đồng bộ ", padding="10")
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self.dry_run_var = tk.BooleanVar(value=False)
        self.dry_run_chk = ttk.Checkbutton(left_pane, text="Chạy thử nghiệm (Dry-Run)", variable=self.dry_run_var)
        self.dry_run_chk.pack(anchor=tk.W, pady=10)



        self.sync_btn = ttk.Button(left_pane, text="ĐỒNG BỘ TIMELINE", command=self.start_sync, style="Accent.TButton")
        self.sync_btn.pack(fill=tk.X, ipady=8, side=tk.BOTTOM, pady=10)

        # Right Pane: Project Table list
        right_pane = ttk.LabelFrame(split_frame, text=" Danh sách dự án (Drafts) ", padding="10")
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))

        # Table Scrollbar
        table_scroll = ttk.Scrollbar(right_pane)
        table_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview (Table)
        self.tree = ttk.Treeview(right_pane, columns=("name", "status"), show="headings", selectmode="browse", yscrollcommand=table_scroll.set)
        self.tree.heading("name", text="Tên dự án (Draft Name)")
        self.tree.heading("status", text="Trạng thái (Status)")
        self.tree.column("name", width=220, anchor=tk.W)
        self.tree.column("status", width=180, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        table_scroll.config(command=self.tree.yview)

        # Bind row selection
        self.selected_project = None
        self.tree.bind("<<TreeviewSelect>>", self.on_project_select)

        # Refresh button
        ttk.Button(right_pane, text="Làm mới (Refresh)", command=self.scan_projects).pack(anchor=tk.E, pady=(10, 0))

        # Bottom Frame: Console Output Log
        log_frame = ttk.LabelFrame(main_frame, text=" Output Log ", padding="5")
        log_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, font=("Consolas", 9), background="#f8f9fa", state=tk.DISABLED, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # Tags for colored outputs
        self.log_text.tag_config("info", foreground="blue")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("warning", foreground="#e67e22") # orange
        self.log_text.tag_config("error", foreground="red")
        
        # Initial scan & load settings
        self.load_settings()
        self.scan_projects()

    def resolve_drafts_dir(self, selected_path):
        if not selected_path:
            return ""
        selected_path = os.path.normpath(selected_path)
        sub_path = os.path.join(selected_path, "User Data", "Projects", "com.lveditor.draft")
        if os.path.exists(sub_path):
            return sub_path
        return selected_path

    def get_default_drafts_dir(self):
        # 1. Check custom path D:\CAIDAT\CAPCUT first since it is user-specific
        custom_path = r"D:\CAIDAT\CAPCUT"
        resolved_custom = self.resolve_drafts_dir(custom_path)
        if os.path.exists(resolved_custom):
            return resolved_custom

        # 2. Standard Windows path fallback
        win_path = os.path.expandvars(r"%LOCALAPPDATA%\CapCut")
        resolved_win = self.resolve_drafts_dir(win_path)
        if os.path.exists(resolved_win):
            return resolved_win
            
        return ""

    def browse_drafts_dir(self):
        dir_selected = filedialog.askdirectory(title="Chọn thư mục cài đặt hoặc thư mục dữ liệu CapCut")
        if dir_selected:
            resolved = self.resolve_drafts_dir(dir_selected)
            self.drafts_dir_var.set(resolved)
            self.scan_projects()
            self.save_settings()

    def browse_timestamps(self):
        file_selected = filedialog.askopenfilename(
            title="Chọn file timestamps (TXT/JSON)",
            filetypes=[
                ("Timestamp Files", "*.txt;*.json"),
                ("Text Files", "*.txt"),
                ("JSON Files", "*.json"),
                ("All Files", "*.*")
            ]
        )
        if file_selected:
            self.timestamps_var.set(os.path.normpath(file_selected))

    def scan_projects(self):
        drafts_dir = self.drafts_dir_var.get()
        # Clear Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not drafts_dir or not os.path.exists(drafts_dir):
            return
        
        try:
            subdirs = [d for d in os.listdir(drafts_dir) if os.path.isdir(os.path.join(drafts_dir, d))]
            subdirs.sort()
            for d in subdirs:
                # Bỏ qua các thư mục ẩn, cache hệ thống hoặc recycle bin (bắt đầu bằng . hoặc _)
                if d.startswith(".") or d.startswith("_"):
                    continue
                
                project_path = os.path.join(drafts_dir, d)
                draft_json = os.path.join(project_path, "draft_content.json")
                
                # Bỏ qua các thư mục không phải là project CapCut (không có file draft_content.json)
                if not os.path.exists(draft_json):
                    continue

                status = "Sẵn sàng (Ready)"
                # Check text readability
                try:
                    with open(draft_json, "r", encoding="utf-8") as f:
                        json.loads(f.read())
                except Exception:
                    status = "Bị mã hóa (Encrypted)"
                
                self.tree.insert("", tk.END, iid=d, values=(d, status))
            
            # Reselect project name if possible
            if self.selected_project in subdirs:
                self.tree.selection_set(self.selected_project)
        except Exception as e:
            self.log(f"Lỗi khi quét các thư mục dự án: {e}\n", "error")

    def on_project_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            self.selected_project = selected_items[0]
            self.save_settings()

    def load_settings(self):
        settings_file = os.path.join(os.path.dirname(__file__), ".gui_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f:
                    data = json.load(f)
                    saved_dir = data.get("drafts_dir", "")
                    if saved_dir and os.path.exists(saved_dir):
                        self.drafts_dir_var.set(saved_dir)
                    self.selected_project = data.get("project_name")
                    self.timestamps_var.set(data.get("timestamps", ""))
            except Exception:
                pass

    def save_settings(self):
        settings_file = os.path.join(os.path.dirname(__file__), ".gui_settings.json")
        try:
            with open(settings_file, "w") as f:
                json.dump({
                    "drafts_dir": self.drafts_dir_var.get(),
                    "project_name": self.selected_project,
                    "timestamps": self.timestamps_var.get()
                }, f)
        except Exception:
            pass

    def log(self, text, tag=None):
        self.log_text.configure(state=tk.NORMAL)
        if tag:
            self.log_text.insert(tk.END, text, tag)
        else:
            self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def start_sync(self):
        drafts_dir = self.drafts_dir_var.get()
        project_name = self.selected_project
        timestamps = self.timestamps_var.get()

        if not drafts_dir or not project_name or not timestamps:
            messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một dự án trong bảng và chọn tệp timestamps (TXT hoặc JSON).")
            return

        self.save_settings()
        self.sync_btn.configure(state=tk.DISABLED)
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

        self.log("Bắt đầu tiến trình đồng bộ...\n", "info")

        # Run script in background thread
        thread = threading.Thread(target=self.run_sync_process, args=(drafts_dir, project_name, timestamps))
        thread.daemon = True
        thread.start()

    def run_sync_process(self, drafts_dir, project_name, timestamps):
        is_json = timestamps.lower().endswith(".json")
        script_name = "sync_capcut_json.py" if is_json else "sync_capcut.py"
        script_path = os.path.join(os.path.dirname(__file__), script_name)
        
        cmd = [
            sys.executable,
            script_path,
            "--drafts-dir", drafts_dir,
            "--project-name", project_name,
            "--timestamps", timestamps
        ]
        if self.dry_run_var.get():
            cmd.append("--dry-run")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8"
            )

            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                # Determine tag based on content
                tag = None
                if "Warning:" in line or "CẢNH BÁO RIÊNG:" in line:
                    tag = "warning"
                elif "Error:" in line or "Traceback" in line:
                    tag = "error"
                elif "thành công!" in line or "Tổng kết:" in line:
                    tag = "success"
                
                self.root.after(0, self.log, line, tag)

            process.wait()
            
            if process.returncode == 0:
                self.root.after(0, self.log, "\nTiến trình hoàn tất thành công.\n", "success")
                # update status in Treeview
                self.root.after(0, self.update_project_status, project_name, "+ Sync Done")
            else:
                self.root.after(0, self.log, f"\nTiến trình kết thúc với mã lỗi: {process.returncode}\n", "error")
                self.root.after(0, self.update_project_status, project_name, "Error")

        except Exception as e:
            self.root.after(0, self.log, f"\nKhông thể khởi chạy script: {e}\n", "error")
        finally:
            self.root.after(0, self.sync_btn.configure, {"state": tk.NORMAL})

    def update_project_status(self, project_name, status_text):
        if self.tree.exists(project_name):
            self.tree.item(project_name, values=(project_name, status_text))

if __name__ == "__main__":
    root = tk.Tk()
    app = CapCutSyncGUI(root)
    root.mainloop()
