import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image

# Import backend modules
from clipper import run_manual_mode, run_auto_mode
from downloader import download_video
from utils import ensure_output_dir, validate_url

class YTCCGui(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Clipper AI - TikTok Edition")
        self.geometry("800x600")
        
        # UI State
        self.is_processing = False
        self.current_video_path = None
        
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create Navigation Frame
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(self.navigation_frame, text="YT Clipper AI",
                                                 font=ctk.CTkFont(size=20, weight="bold"))
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.home_button = ctk.CTkButton(self.navigation_frame, corner_radius=0, height=40, border_spacing=10, text="Create Clips",
                                         fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                                         anchor="w", command=self.home_button_event)
        self.home_button.grid(row=1, column=0, sticky="ew")

        # Create Main Frame
        self.home_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.setup_home_frame()

        # Initialize with home frame
        self.home_button_event()

    def setup_home_frame(self):
        # URL Input
        self.url_label = ctk.CTkLabel(self.home_frame, text="YouTube URL:")
        self.url_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.url_entry = ctk.CTkEntry(self.home_frame, placeholder_text="https://www.youtube.com/watch?v=...", width=400)
        self.url_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Mode Selection
        self.mode_label = ctk.CTkLabel(self.home_frame, text="Mode:")
        self.mode_label.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.mode_var = ctk.StringVar(value="Manual")
        self.manual_radio = ctk.CTkRadioButton(self.home_frame, text="Manual (Start/End)", variable=self.mode_var, value="Manual", command=self.update_mode_ui)
        self.manual_radio.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        
        self.auto_radio = ctk.CTkRadioButton(self.home_frame, text="Auto (AI Highlights)", variable=self.mode_var, value="Auto", command=self.update_mode_ui)
        self.auto_radio.grid(row=3, column=1, padx=20, pady=5, sticky="w")

        # Manual Options Frame
        self.manual_frame = ctk.CTkFrame(self.home_frame)
        self.manual_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.start_label = ctk.CTkLabel(self.manual_frame, text="Start (MM:SS):")
        self.start_label.grid(row=0, column=0, padx=10, pady=5)
        self.start_entry = ctk.CTkEntry(self.manual_frame, placeholder_text="00:00", width=100)
        self.start_entry.grid(row=0, column=1, padx=10, pady=5)
        
        self.end_label = ctk.CTkLabel(self.manual_frame, text="End (MM:SS):")
        self.end_label.grid(row=0, column=2, padx=10, pady=5)
        self.end_entry = ctk.CTkEntry(self.manual_frame, placeholder_text="00:30", width=100)
        self.end_entry.grid(row=0, column=3, padx=10, pady=5)

        # Auto Options Frame (Hidden initially)
        self.auto_frame = ctk.CTkFrame(self.home_frame)
        # grid() will be called in update_mode_ui
        
        self.max_clips_label = ctk.CTkLabel(self.auto_frame, text="Max Clips:")
        self.max_clips_label.grid(row=0, column=0, padx=10, pady=5)
        self.max_clips_slider = ctk.CTkSlider(self.auto_frame, from_=1, to=10, number_of_steps=9)
        self.max_clips_slider.set(3)
        self.max_clips_slider.grid(row=0, column=1, padx=10, pady=5)
        self.max_clips_val = ctk.CTkLabel(self.auto_frame, text="3")
        self.max_clips_val.grid(row=0, column=2, padx=10, pady=5)
        self.max_clips_slider.configure(command=lambda v: self.max_clips_val.configure(text=str(int(v))))

        # Global Options
        self.options_frame = ctk.CTkFrame(self.home_frame)
        self.options_frame.grid(row=6, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        self.face_track_var = ctk.BooleanVar(value=True)
        self.face_track_cb = ctk.CTkCheckBox(self.options_frame, text="Use AI Face Tracking", variable=self.face_track_var)
        self.face_track_cb.grid(row=0, column=0, padx=20, pady=10)
        
        self.quality_label = ctk.CTkLabel(self.options_frame, text="Quality:")
        self.quality_label.grid(row=0, column=1, padx=10, pady=10)
        self.quality_menu = ctk.CTkOptionMenu(self.options_frame, values=["high", "medium", "low"])
        self.quality_menu.grid(row=0, column=2, padx=10, pady=10)

        # Progress Section
        self.progress_label = ctk.CTkLabel(self.home_frame, text="Ready", font=ctk.CTkFont(weight="bold"))
        self.progress_label.grid(row=7, column=0, columnspan=2, pady=(20, 0))
        
        self.progress_bar = ctk.CTkProgressBar(self.home_frame)
        self.progress_bar.grid(row=8, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # Action Button
        self.start_btn = ctk.CTkButton(self.home_frame, text="Generate Clip(s)", command=self.start_process, height=40, font=ctk.CTkFont(size=15, weight="bold"))
        self.start_btn.grid(row=9, column=0, columnspan=2, padx=20, pady=20, sticky="ew")

        # Output Log
        self.log_text = ctk.CTkTextbox(self.home_frame, height=100)
        self.log_text.grid(row=10, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.log_text.insert("0.0", "System Log:\n")
        self.log_text.configure(state="disabled")

    def log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"> {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_mode_ui(self):
        if self.mode_var.get() == "Manual":
            self.auto_frame.grid_forget()
            self.manual_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        else:
            self.manual_frame.grid_forget()
            self.auto_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

    def home_button_event(self):
        self.home_frame.grid(row=0, column=1, sticky="nsew")

    def progress_callback(self, percentage, status_text=None):
        def update():
            self.progress_bar.set(percentage / 100)
            if status_text:
                self.progress_label.configure(text=status_text)
        self.after(0, update)

    def start_process(self):
        url = self.url_entry.get()
        if not validate_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
            
        if self.is_processing:
            return
            
        self.is_processing = True
        self.start_btn.configure(state="disabled")
        self.log("Starting process...")
        
        # Run in background thread
        thread = threading.Thread(target=self.process_thread, args=(url,), daemon=True)
        thread.start()

    def process_thread(self, url):
        try:
            output_dir = ensure_output_dir("output")
            
            # Step 1: Download
            self.progress_callback(0, "Downloading Video...")
            video_path = download_video(
                url=url, 
                output_dir=output_dir, 
                progress_callback=lambda p: self.progress_callback(p, f"Downloading: {p}%")
            )
            
            if not video_path:
                raise Exception("Failed to download video")
                
            self.current_video_path = video_path
            self.log(f"Video downloaded to {video_path}")
            
            # Step 2: Process Clips
            quality = self.quality_menu.get()
            use_ft = self.face_track_var.get()
            
            if self.mode_var.get() == "Manual":
                start_time = self.start_entry.get()
                end_time = self.end_entry.get()
                
                self.progress_callback(0, "Processing Clip...")
                result = run_manual_mode(
                    video_path=video_path,
                    start_time=start_time,
                    end_time=end_time,
                    output_dir=output_dir,
                    quality=quality,
                    use_face_tracking=use_ft,
                    verbose=True
                    # Note: We might need to pass progress_callback to run_manual_mode too
                )
                if result:
                    self.log(f"Clip created: {result}")
            else:
                max_clips = int(self.max_clips_slider.get())
                self.progress_callback(0, "Detecting Highlights...")
                results = run_auto_mode(
                    video_path=video_path,
                    output_dir=output_dir,
                    max_clips=max_clips,
                    min_duration=15,
                    max_duration=60,
                    quality=quality,
                    use_face_tracking=use_ft,
                    verbose=True
                )
                self.log(f"Created {len(results)} clips")
                for r in results: self.log(f"  - {r}")

            self.progress_callback(100, "Done!")
            self.after(0, lambda: messagebox.showinfo("Success", "Process completed successfully!"))

        except Exception as e:
            self.log(f"Error: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Process Error", str(e)))
        finally:
            self.is_processing = False
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            # Optional cleanup
            # if os.path.exists(video_path): os.remove(video_path)

if __name__ == "__main__":
    app = YTCCGui()
    app.mainloop()
