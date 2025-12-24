"""
Auto Click Tool - Windows Automation Tool
Công cụ tự động hóa thao tác chuột và bàn phím
"""

import customtkinter as ctk
import pyautogui
import keyboard
import threading
import time
import json
import os
import cv2
import numpy as np
from PIL import Image, ImageGrab, ImageTk
from pynput import mouse, keyboard as pynput_keyboard
from datetime import datetime
from tkinter import filedialog

# Cấu hình pyautogui
pyautogui.FAILSAFE = True  # Di chuyển chuột góc trên bên trái để dừng
pyautogui.PAUSE = 0.1

class AutoClickTool:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Auto Click Tool")
        self.root.geometry("500x650")
        self.root.resizable(False, False)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # State variables
        self.is_clicking = False
        self.is_recording = False
        self.is_image_clicking = False
        self.recorded_actions = []
        self.click_thread = None
        self.playback_thread = None
        self.image_click_thread = None
        self.record_start_time = None
        
        # Image recognition
        self.image_targets = []  # List of {"path": str, "confidence": float, "click_type": str}
        self.current_profile = "Default"
        self.profiles_dir = os.path.join(os.path.dirname(__file__), "profiles")
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Workflow (luồng thao tác)
        self.workflow_steps = []  # List of workflow steps
        self.is_workflow_running = False
        self.workflow_thread = None
        self.workflows_dir = os.path.join(os.path.dirname(__file__), "workflows")
        os.makedirs(self.workflows_dir, exist_ok=True)
        
        # Mouse listener for recording
        self.mouse_listener = None
        self.keyboard_listener = None
        
        self.setup_ui()
        self.setup_hotkeys()
        
    def setup_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title = ctk.CTkLabel(main_frame, text="🖱️ Auto Click Tool", font=("Arial", 24, "bold"))
        title.pack(pady=10)
        
        # Tab view
        self.tabview = ctk.CTkTabview(main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tabs
        self.tab_autoclick = self.tabview.add("Auto Click")
        self.tab_image = self.tabview.add("Click bằng hình ảnh")
        self.tab_workflow = self.tabview.add("Click theo luồng thao tác")
        self.tab_record = self.tabview.add("Macro")
        self.tab_settings = self.tabview.add("Cài đặt")
        
        self.setup_autoclick_tab()
        self.setup_image_tab()
        self.setup_workflow_tab()
        self.setup_record_tab()
        self.setup_settings_tab()
        
        # Status bar
        self.status_var = ctk.StringVar(value="Sẵn sàng | F6: Auto Click | F9: Tìm hình | F10: Luồng | F7: Ghi | F8: Phát")
        status_bar = ctk.CTkLabel(main_frame, textvariable=self.status_var, font=("Arial", 10))
        status_bar.pack(pady=5)
        
    def setup_autoclick_tab(self):
        frame = self.tab_autoclick
        
        # Click type
        type_frame = ctk.CTkFrame(frame)
        type_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(type_frame, text="Loại click:", font=("Arial", 12)).pack(side="left", padx=5)
        self.click_type = ctk.CTkComboBox(type_frame, values=["Click trái", "Click phải", "Double click"])
        self.click_type.pack(side="left", padx=5)
        self.click_type.set("Click trái")
        
        # Interval
        interval_frame = ctk.CTkFrame(frame)
        interval_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(interval_frame, text="Khoảng cách (ms):", font=("Arial", 12)).pack(side="left", padx=5)
        self.interval_entry = ctk.CTkEntry(interval_frame, width=100)
        self.interval_entry.pack(side="left", padx=5)
        self.interval_entry.insert(0, "100")
        
        # Click count
        count_frame = ctk.CTkFrame(frame)
        count_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(count_frame, text="Số lần click:", font=("Arial", 12)).pack(side="left", padx=5)
        self.click_count = ctk.CTkEntry(count_frame, width=100)
        self.click_count.pack(side="left", padx=5)
        self.click_count.insert(0, "0")
        ctk.CTkLabel(count_frame, text="(0 = vô hạn)", font=("Arial", 10)).pack(side="left", padx=5)
        
        # Position
        pos_frame = ctk.CTkFrame(frame)
        pos_frame.pack(fill="x", padx=10, pady=5)
        
        self.use_current_pos = ctk.CTkCheckBox(pos_frame, text="Dùng vị trí hiện tại của chuột")
        self.use_current_pos.pack(side="left", padx=5)
        self.use_current_pos.select()
        
        # Custom position
        custom_pos_frame = ctk.CTkFrame(frame)
        custom_pos_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(custom_pos_frame, text="X:", font=("Arial", 12)).pack(side="left", padx=5)
        self.pos_x = ctk.CTkEntry(custom_pos_frame, width=70)
        self.pos_x.pack(side="left", padx=5)
        self.pos_x.insert(0, "0")
        
        ctk.CTkLabel(custom_pos_frame, text="Y:", font=("Arial", 12)).pack(side="left", padx=5)
        self.pos_y = ctk.CTkEntry(custom_pos_frame, width=70)
        self.pos_y.pack(side="left", padx=5)
        self.pos_y.insert(0, "0")
        
        get_pos_btn = ctk.CTkButton(custom_pos_frame, text="Lấy vị trí", width=80, command=self.get_mouse_position)
        get_pos_btn.pack(side="left", padx=5)
        
        # Current position display
        self.current_pos_label = ctk.CTkLabel(frame, text="Vị trí chuột: (0, 0)", font=("Arial", 11))
        self.current_pos_label.pack(pady=5)
        self.update_mouse_position()
        
        # Start/Stop button
        self.start_btn = ctk.CTkButton(frame, text="▶ Bắt đầu (F6)", font=("Arial", 14, "bold"),
                                        height=50, command=self.toggle_clicking)
        self.start_btn.pack(pady=20, padx=20, fill="x")

    def setup_image_tab(self):
        frame = self.tab_image
        
        # Info
        info_label = ctk.CTkLabel(frame, text="🔍 Tự động tìm và click vào hình ảnh trên màn hình",
                                   font=("Arial", 12))
        info_label.pack(pady=5)
        
        # Profile section
        profile_frame = ctk.CTkFrame(frame)
        profile_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(profile_frame, text="📁 Profile:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        
        self.profile_combo = ctk.CTkComboBox(profile_frame, values=self.get_profile_list(), width=150,
                                              command=self.on_profile_change)
        self.profile_combo.pack(side="left", padx=5)
        self.profile_combo.set(self.current_profile)
        
        new_profile_btn = ctk.CTkButton(profile_frame, text="➕ Mới", width=60, command=self.create_new_profile)
        new_profile_btn.pack(side="left", padx=3)
        
        save_profile_btn = ctk.CTkButton(profile_frame, text="💾 Lưu", width=60, command=self.save_current_profile)
        save_profile_btn.pack(side="left", padx=3)
        
        del_profile_btn = ctk.CTkButton(profile_frame, text="🗑️", width=40, fg_color="red", 
                                         command=self.delete_current_profile)
        del_profile_btn.pack(side="left", padx=3)
        
        # Add image section
        add_frame = ctk.CTkFrame(frame)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        # Buttons row
        btn_row = ctk.CTkFrame(add_frame)
        btn_row.pack(fill="x", padx=5, pady=5)
        
        add_file_btn = ctk.CTkButton(btn_row, text="📁 Thêm từ file", width=120, command=self.add_image_from_file)
        add_file_btn.pack(side="left", padx=5)
        
        capture_btn = ctk.CTkButton(btn_row, text="📷 Chụp vùng màn hình", width=150, command=self.capture_screen_region)
        capture_btn.pack(side="left", padx=5)
        
        # Confidence slider
        conf_frame = ctk.CTkFrame(add_frame)
        conf_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(conf_frame, text="Độ chính xác:", font=("Arial", 11)).pack(side="left", padx=5)
        self.confidence_slider = ctk.CTkSlider(conf_frame, from_=0.5, to=1.0, width=150)
        self.confidence_slider.pack(side="left", padx=5)
        self.confidence_slider.set(0.8)
        self.confidence_label = ctk.CTkLabel(conf_frame, text="80%", font=("Arial", 11))
        self.confidence_label.pack(side="left", padx=5)
        self.confidence_slider.configure(command=self.update_confidence_label)
        
        # Click type for image
        ctk.CTkLabel(conf_frame, text="Click:", font=("Arial", 11)).pack(side="left", padx=5)
        self.image_click_type = ctk.CTkComboBox(conf_frame, values=["Trái", "Phải", "Double"], width=80)
        self.image_click_type.pack(side="left", padx=5)
        self.image_click_type.set("Trái")
        
        # Image list
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(list_frame, text="Danh sách hình ảnh mục tiêu:", font=("Arial", 12)).pack(anchor="w", padx=5)
        
        # Scrollable frame for images
        self.image_list_frame = ctk.CTkScrollableFrame(list_frame, height=150)
        self.image_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scan settings
        scan_frame = ctk.CTkFrame(frame)
        scan_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(scan_frame, text="Quét mỗi (ms):", font=("Arial", 11)).pack(side="left", padx=5)
        self.scan_interval = ctk.CTkEntry(scan_frame, width=70)
        self.scan_interval.pack(side="left", padx=5)
        self.scan_interval.insert(0, "500")
        
        self.continuous_scan = ctk.CTkCheckBox(scan_frame, text="Quét liên tục")
        self.continuous_scan.pack(side="left", padx=10)
        self.continuous_scan.select()
        
        # Control buttons
        ctrl_frame = ctk.CTkFrame(frame)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        self.image_start_btn = ctk.CTkButton(ctrl_frame, text="▶ Bắt đầu tìm (F9)", font=("Arial", 14, "bold"),
                                              height=45, command=self.toggle_image_clicking, fg_color="green")
        self.image_start_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        clear_img_btn = ctk.CTkButton(ctrl_frame, text="🗑️ Xóa tất cả", width=100, 
                                       command=self.clear_image_targets, fg_color="gray")
        clear_img_btn.pack(side="left", padx=5)
        
        # Test button
        test_btn = ctk.CTkButton(frame, text="🔍 Test tìm kiếm (không click)", command=self.test_image_search)
        test_btn.pack(pady=5, padx=10, fill="x")
    
    def setup_workflow_tab(self):
        """Tab luồng thao tác - auto click theo chuỗi các bước"""
        frame = self.tab_workflow
        
        # Info
        info_label = ctk.CTkLabel(frame, text="🔄 Tạo luồng thao tác tự động theo thứ tự",
                                   font=("Arial", 12))
        info_label.pack(pady=5)
        
        # Add step section
        add_frame = ctk.CTkFrame(frame)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(add_frame, text="Thêm bước mới:", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=3)
        
        # Step type selection
        type_row = ctk.CTkFrame(add_frame)
        type_row.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(type_row, text="Loại:", font=("Arial", 11)).pack(side="left", padx=5)
        self.workflow_step_type = ctk.CTkComboBox(type_row, values=[
            "Click trái", "Click phải", "Double click", 
            "Chờ (delay)", "Tìm hình & click", "Nhập text", "Nhấn phím"
        ], width=140, command=self.on_workflow_type_change)
        self.workflow_step_type.pack(side="left", padx=5)
        self.workflow_step_type.set("Click trái")
        
        # Position row
        pos_row = ctk.CTkFrame(add_frame)
        pos_row.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(pos_row, text="X:", font=("Arial", 11)).pack(side="left", padx=5)
        self.wf_pos_x = ctk.CTkEntry(pos_row, width=60)
        self.wf_pos_x.pack(side="left", padx=3)
        self.wf_pos_x.insert(0, "0")
        
        ctk.CTkLabel(pos_row, text="Y:", font=("Arial", 11)).pack(side="left", padx=5)
        self.wf_pos_y = ctk.CTkEntry(pos_row, width=60)
        self.wf_pos_y.pack(side="left", padx=3)
        self.wf_pos_y.insert(0, "0")
        
        get_pos_btn = ctk.CTkButton(pos_row, text="📍 Lấy vị trí", width=90, command=self.get_workflow_position)
        get_pos_btn.pack(side="left", padx=5)
        
        # Value row (for delay, text, key)
        value_row = ctk.CTkFrame(add_frame)
        value_row.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(value_row, text="Giá trị:", font=("Arial", 11)).pack(side="left", padx=5)
        self.wf_value = ctk.CTkEntry(value_row, width=200, placeholder_text="ms / text / phím")
        self.wf_value.pack(side="left", padx=5)
        
        # Image selection for "Tìm hình & click"
        img_row = ctk.CTkFrame(add_frame)
        img_row.pack(fill="x", padx=5, pady=3)
        
        self.wf_image_btn = ctk.CTkButton(img_row, text="📷 Chọn hình ảnh", width=120, command=self.select_workflow_image)
        self.wf_image_btn.pack(side="left", padx=5)
        
        self.wf_image_label = ctk.CTkLabel(img_row, text="Chưa chọn", font=("Arial", 10))
        self.wf_image_label.pack(side="left", padx=5)
        
        self.wf_selected_image = None
        
        # Add button
        add_btn = ctk.CTkButton(add_frame, text="➕ Thêm bước", command=self.add_workflow_step, fg_color="green")
        add_btn.pack(pady=5, padx=5, fill="x")
        
        # Steps list
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        list_header = ctk.CTkFrame(list_frame)
        list_header.pack(fill="x", padx=5, pady=3)
        
        ctk.CTkLabel(list_header, text="Danh sách các bước:", font=("Arial", 12, "bold")).pack(side="left")
        
        clear_steps_btn = ctk.CTkButton(list_header, text="🗑️ Xóa tất cả", width=90, fg_color="gray",
                                         command=self.clear_workflow_steps)
        clear_steps_btn.pack(side="right", padx=5)
        
        self.workflow_list_frame = ctk.CTkScrollableFrame(list_frame, height=120)
        self.workflow_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Loop settings
        loop_frame = ctk.CTkFrame(frame)
        loop_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(loop_frame, text="Số lần lặp:", font=("Arial", 11)).pack(side="left", padx=5)
        self.wf_loop_count = ctk.CTkEntry(loop_frame, width=60)
        self.wf_loop_count.pack(side="left", padx=5)
        self.wf_loop_count.insert(0, "1")
        ctk.CTkLabel(loop_frame, text="(0 = vô hạn)", font=("Arial", 10)).pack(side="left", padx=5)
        
        self.wf_stop_on_error = ctk.CTkCheckBox(loop_frame, text="Dừng khi lỗi")
        self.wf_stop_on_error.pack(side="left", padx=10)
        self.wf_stop_on_error.select()
        
        # Control buttons
        ctrl_frame = ctk.CTkFrame(frame)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        self.workflow_start_btn = ctk.CTkButton(ctrl_frame, text="▶ Chạy luồng (F10)", font=("Arial", 14, "bold"),
                                                 height=45, command=self.toggle_workflow, fg_color="green")
        self.workflow_start_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        # Save/Load
        file_frame = ctk.CTkFrame(frame)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        save_wf_btn = ctk.CTkButton(file_frame, text="💾 Lưu luồng", width=100, command=self.save_workflow)
        save_wf_btn.pack(side="left", padx=5, expand=True)
        
        load_wf_btn = ctk.CTkButton(file_frame, text="📂 Tải luồng", width=100, command=self.load_workflow)
        load_wf_btn.pack(side="left", padx=5, expand=True)
    
    def on_workflow_type_change(self, value):
        """Cập nhật UI khi thay đổi loại bước"""
        pass  # Có thể thêm logic ẩn/hiện các field tùy loại
    
    def get_workflow_position(self):
        """Lấy vị trí chuột hiện tại cho workflow"""
        x, y = pyautogui.position()
        self.wf_pos_x.delete(0, "end")
        self.wf_pos_x.insert(0, str(x))
        self.wf_pos_y.delete(0, "end")
        self.wf_pos_y.insert(0, str(y))
    
    def select_workflow_image(self):
        """Chọn hình ảnh cho bước tìm hình"""
        filepath = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        if filepath:
            self.wf_selected_image = filepath
            self.wf_image_label.configure(text=os.path.basename(filepath))
    
    def add_workflow_step(self):
        """Thêm một bước vào luồng"""
        step_type = self.workflow_step_type.get()
        
        step = {
            "type": step_type,
            "x": int(self.wf_pos_x.get() or 0),
            "y": int(self.wf_pos_y.get() or 0),
            "value": self.wf_value.get(),
            "image": self.wf_selected_image
        }
        
        # Validate
        if step_type == "Chờ (delay)" and not step["value"]:
            self.status_var.set("Vui lòng nhập thời gian chờ (ms)!")
            return
        if step_type == "Tìm hình & click" and not step["image"]:
            self.status_var.set("Vui lòng chọn hình ảnh!")
            return
        if step_type == "Nhập text" and not step["value"]:
            self.status_var.set("Vui lòng nhập text!")
            return
        if step_type == "Nhấn phím" and not step["value"]:
            self.status_var.set("Vui lòng nhập phím!")
            return
        
        self.workflow_steps.append(step)
        self.refresh_workflow_list()
        self.status_var.set(f"Đã thêm bước: {step_type}")
        
        # Reset image selection
        self.wf_selected_image = None
        self.wf_image_label.configure(text="Chưa chọn")
    
    def refresh_workflow_list(self):
        """Cập nhật danh sách các bước trong UI"""
        for widget in self.workflow_list_frame.winfo_children():
            widget.destroy()
        
        for i, step in enumerate(self.workflow_steps):
            row = ctk.CTkFrame(self.workflow_list_frame)
            row.pack(fill="x", pady=2)
            
            # Step number
            ctk.CTkLabel(row, text=f"{i+1}.", font=("Arial", 11, "bold"), width=25).pack(side="left", padx=3)
            
            # Step description
            desc = self.get_step_description(step)
            ctk.CTkLabel(row, text=desc, font=("Arial", 10), anchor="w").pack(side="left", padx=5, expand=True, fill="x")
            
            # Move buttons
            up_btn = ctk.CTkButton(row, text="↑", width=25, height=25, 
                                    command=lambda idx=i: self.move_workflow_step(idx, -1))
            up_btn.pack(side="left", padx=2)
            
            down_btn = ctk.CTkButton(row, text="↓", width=25, height=25,
                                      command=lambda idx=i: self.move_workflow_step(idx, 1))
            down_btn.pack(side="left", padx=2)
            
            # Delete button
            del_btn = ctk.CTkButton(row, text="✕", width=25, height=25, fg_color="red",
                                     command=lambda idx=i: self.remove_workflow_step(idx))
            del_btn.pack(side="left", padx=2)
    
    def get_step_description(self, step):
        """Tạo mô tả cho một bước"""
        step_type = step["type"]
        if step_type in ["Click trái", "Click phải", "Double click"]:
            return f"{step_type} tại ({step['x']}, {step['y']})"
        elif step_type == "Chờ (delay)":
            return f"Chờ {step['value']}ms"
        elif step_type == "Tìm hình & click":
            img_name = os.path.basename(step['image']) if step['image'] else "?"
            return f"Tìm & click: {img_name}"
        elif step_type == "Nhập text":
            text = step['value'][:20] + "..." if len(step['value']) > 20 else step['value']
            return f"Nhập: \"{text}\""
        elif step_type == "Nhấn phím":
            return f"Nhấn phím: {step['value']}"
        return step_type
    
    def move_workflow_step(self, index, direction):
        """Di chuyển bước lên/xuống"""
        new_index = index + direction
        if 0 <= new_index < len(self.workflow_steps):
            self.workflow_steps[index], self.workflow_steps[new_index] = \
                self.workflow_steps[new_index], self.workflow_steps[index]
            self.refresh_workflow_list()
    
    def remove_workflow_step(self, index):
        """Xóa một bước"""
        if 0 <= index < len(self.workflow_steps):
            self.workflow_steps.pop(index)
            self.refresh_workflow_list()
    
    def clear_workflow_steps(self):
        """Xóa tất cả các bước"""
        self.workflow_steps = []
        self.refresh_workflow_list()
        self.status_var.set("Đã xóa tất cả các bước")
    
    def toggle_workflow(self):
        """Bật/tắt chạy luồng"""
        if self.is_workflow_running:
            self.stop_workflow()
        else:
            self.start_workflow()
    
    def start_workflow(self):
        """Bắt đầu chạy luồng"""
        if not self.workflow_steps:
            self.status_var.set("Chưa có bước nào trong luồng!")
            return
        
        self.is_workflow_running = True
        self.workflow_start_btn.configure(text="⏹ Dừng (F10)", fg_color="red")
        self.status_var.set("Đang chạy luồng...")
        
        self.workflow_thread = threading.Thread(target=self.workflow_loop, daemon=True)
        self.workflow_thread.start()
    
    def stop_workflow(self):
        """Dừng luồng"""
        self.is_workflow_running = False
        self.workflow_start_btn.configure(text="▶ Chạy luồng (F10)", fg_color="green")
        self.status_var.set("Đã dừng luồng")
    
    def workflow_loop(self):
        """Vòng lặp thực hiện các bước trong luồng"""
        try:
            loop_count = int(self.wf_loop_count.get() or 1)
            stop_on_error = self.wf_stop_on_error.get()
            
            iteration = 0
            while self.is_workflow_running:
                iteration += 1
                
                if loop_count > 0 and iteration > loop_count:
                    break
                
                self.root.after(0, lambda i=iteration, t=loop_count: 
                    self.status_var.set(f"Luồng: lần {i}/{t if t > 0 else '∞'}"))
                
                for step_idx, step in enumerate(self.workflow_steps):
                    if not self.is_workflow_running:
                        break
                    
                    success = self.execute_workflow_step(step, step_idx)
                    
                    if not success and stop_on_error:
                        self.root.after(0, lambda: self.status_var.set("Luồng dừng do lỗi!"))
                        self.root.after(0, self.stop_workflow)
                        return
                
                # Delay nhỏ giữa các lần lặp
                time.sleep(0.1)
            
            self.root.after(0, self.stop_workflow)
            self.root.after(0, lambda: self.status_var.set("Luồng hoàn tất!"))
            
        except Exception as e:
            print(f"Workflow error: {e}")
            self.root.after(0, self.stop_workflow)
    
    def execute_workflow_step(self, step, step_idx):
        """Thực hiện một bước trong luồng"""
        try:
            step_type = step["type"]
            
            if step_type == "Click trái":
                pyautogui.click(step["x"], step["y"])
            elif step_type == "Click phải":
                pyautogui.rightClick(step["x"], step["y"])
            elif step_type == "Double click":
                pyautogui.doubleClick(step["x"], step["y"])
            elif step_type == "Chờ (delay)":
                delay_ms = int(step["value"])
                time.sleep(delay_ms / 1000)
            elif step_type == "Tìm hình & click":
                return self.execute_find_and_click(step)
            elif step_type == "Nhập text":
                pyautogui.typewrite(step["value"], interval=0.02)
            elif step_type == "Nhấn phím":
                pyautogui.press(step["value"])
            
            return True
        except Exception as e:
            print(f"Step {step_idx + 1} error: {e}")
            return False
    
    def execute_find_and_click(self, step):
        """Tìm hình ảnh và click"""
        try:
            screenshot = np.array(ImageGrab.grab())
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            template = cv2.imread(step["image"])
            if template is None:
                return False
            
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= 0.8:  # Default confidence
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                pyautogui.click(center_x, center_y)
                return True
            
            return False
        except Exception as e:
            print(f"Find and click error: {e}")
            return False
    
    def save_workflow(self):
        """Lưu luồng ra file"""
        if not self.workflow_steps:
            self.status_var.set("Không có bước nào để lưu!")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Lưu luồng thao tác",
            defaultextension=".json",
            initialdir=self.workflows_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            data = {
                "steps": self.workflow_steps,
                "loop_count": self.wf_loop_count.get(),
                "stop_on_error": self.wf_stop_on_error.get()
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.status_var.set(f"Đã lưu: {os.path.basename(filepath)}")
    
    def load_workflow(self):
        """Tải luồng từ file"""
        filepath = filedialog.askopenfilename(
            title="Tải luồng thao tác",
            initialdir=self.workflows_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.workflow_steps = data.get("steps", [])
                
                self.wf_loop_count.delete(0, "end")
                self.wf_loop_count.insert(0, data.get("loop_count", "1"))
                
                if data.get("stop_on_error", True):
                    self.wf_stop_on_error.select()
                else:
                    self.wf_stop_on_error.deselect()
                
                self.refresh_workflow_list()
                self.status_var.set(f"Đã tải: {len(self.workflow_steps)} bước")
            except Exception as e:
                self.status_var.set(f"Lỗi tải file: {e}")
    
    def update_confidence_label(self, value):
        self.confidence_label.configure(text=f"{int(float(value)*100)}%")
    
    # ===== PROFILE MANAGEMENT =====
    def get_profile_list(self):
        """Lấy danh sách các profile đã lưu"""
        profiles = ["Default"]
        if os.path.exists(self.profiles_dir):
            for f in os.listdir(self.profiles_dir):
                if f.endswith('.json'):
                    name = f[:-5]  # Remove .json
                    if name not in profiles:
                        profiles.append(name)
        return profiles
    
    def refresh_profile_combo(self):
        """Cập nhật danh sách profile trong combobox"""
        profiles = self.get_profile_list()
        self.profile_combo.configure(values=profiles)
    
    def on_profile_change(self, profile_name):
        """Khi chọn profile khác"""
        if profile_name != self.current_profile:
            self.load_profile(profile_name)
    
    def create_new_profile(self):
        """Tạo profile mới"""
        dialog = ctk.CTkInputDialog(text="Nhập tên profile mới:", title="Tạo Profile")
        name = dialog.get_input()
        
        if name and name.strip():
            name = name.strip()
            # Kiểm tra tên hợp lệ
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(c in name for c in invalid_chars):
                self.status_var.set("Tên profile không hợp lệ!")
                return
            
            self.current_profile = name
            self.image_targets = []
            self.refresh_image_list()
            self.refresh_profile_combo()
            self.profile_combo.set(name)
            self.status_var.set(f"Đã tạo profile mới: {name}")
    
    def save_current_profile(self):
        """Lưu profile hiện tại"""
        if not self.image_targets:
            self.status_var.set("Không có hình ảnh nào để lưu!")
            return
        
        profile_data = {
            "name": self.current_profile,
            "targets": self.image_targets,
            "scan_interval": self.scan_interval.get(),
            "continuous": self.continuous_scan.get()
        }
        
        filepath = os.path.join(self.profiles_dir, f"{self.current_profile}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        self.refresh_profile_combo()
        self.status_var.set(f"Đã lưu profile: {self.current_profile}")
    
    def load_profile(self, profile_name):
        """Tải profile"""
        filepath = os.path.join(self.profiles_dir, f"{profile_name}.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                
                self.current_profile = profile_name
                self.image_targets = profile_data.get("targets", [])
                
                # Restore settings
                self.scan_interval.delete(0, "end")
                self.scan_interval.insert(0, profile_data.get("scan_interval", "500"))
                
                if profile_data.get("continuous", True):
                    self.continuous_scan.select()
                else:
                    self.continuous_scan.deselect()
                
                self.refresh_image_list()
                self.status_var.set(f"Đã tải profile: {profile_name} ({len(self.image_targets)} ảnh)")
            except Exception as e:
                self.status_var.set(f"Lỗi tải profile: {e}")
        else:
            # Profile mới chưa có file
            self.current_profile = profile_name
            self.image_targets = []
            self.refresh_image_list()
            self.status_var.set(f"Profile: {profile_name} (trống)")
    
    def delete_current_profile(self):
        """Xóa profile hiện tại"""
        if self.current_profile == "Default":
            self.status_var.set("Không thể xóa profile Default!")
            return
        
        filepath = os.path.join(self.profiles_dir, f"{self.current_profile}.json")
        
        if os.path.exists(filepath):
            os.remove(filepath)
        
        deleted_name = self.current_profile
        self.current_profile = "Default"
        self.image_targets = []
        self.refresh_image_list()
        self.refresh_profile_combo()
        self.profile_combo.set("Default")
        self.status_var.set(f"Đã xóa profile: {deleted_name}")
    
    # ===== END PROFILE MANAGEMENT =====
    
    def add_image_from_file(self):
        filepath = filedialog.askopenfilename(
            title="Chọn hình ảnh",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")]
        )
        
        if filepath:
            self.add_image_target(filepath)
    
    def capture_screen_region(self):
        """Mở cửa sổ để chụp vùng màn hình"""
        self.root.iconify()  # Thu nhỏ cửa sổ chính
        time.sleep(0.3)
        
        # Tạo overlay để chọn vùng
        capture_window = ctk.CTkToplevel()
        capture_window.attributes('-fullscreen', True)
        capture_window.attributes('-alpha', 0.3)
        capture_window.attributes('-topmost', True)
        capture_window.configure(fg_color='gray')
        
        # Variables for selection
        self.capture_start = None
        self.capture_rect = None
        
        canvas = ctk.CTkCanvas(capture_window, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        instruction = ctk.CTkLabel(capture_window, text="Kéo chuột để chọn vùng cần chụp | ESC để hủy",
                                    font=("Arial", 16, "bold"), fg_color="black", text_color="white")
        instruction.place(relx=0.5, y=30, anchor="center")
        
        def on_press(event):
            self.capture_start = (event.x, event.y)
            if self.capture_rect:
                canvas.delete(self.capture_rect)
        
        def on_drag(event):
            if self.capture_start:
                if self.capture_rect:
                    canvas.delete(self.capture_rect)
                self.capture_rect = canvas.create_rectangle(
                    self.capture_start[0], self.capture_start[1],
                    event.x, event.y, outline='red', width=2
                )
        
        def on_release(event):
            if self.capture_start:
                x1, y1 = self.capture_start
                x2, y2 = event.x, event.y
                
                # Ensure correct order
                left = min(x1, x2)
                top = min(y1, y2)
                right = max(x1, x2)
                bottom = max(y1, y2)
                
                if right - left > 10 and bottom - top > 10:
                    capture_window.destroy()
                    time.sleep(0.2)
                    
                    # Capture the region
                    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
                    
                    # Save to file
                    os.makedirs(os.path.join(os.path.dirname(__file__), "captures"), exist_ok=True)
                    filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    filepath = os.path.join(os.path.dirname(__file__), "captures", filename)
                    screenshot.save(filepath)
                    
                    self.root.deiconify()
                    self.add_image_target(filepath)
                    self.status_var.set(f"Đã chụp và lưu: {filename}")
        
        def on_escape(event):
            capture_window.destroy()
            self.root.deiconify()
        
        canvas.bind('<Button-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        capture_window.bind('<Escape>', on_escape)
    
    def add_image_target(self, filepath):
        """Thêm hình ảnh vào danh sách mục tiêu"""
        confidence = self.confidence_slider.get()
        click_type = self.image_click_type.get()
        
        target = {
            "path": filepath,
            "confidence": confidence,
            "click_type": click_type,
            "name": os.path.basename(filepath)
        }
        self.image_targets.append(target)
        
        # Add to UI
        self.refresh_image_list()
        self.status_var.set(f"Đã thêm: {target['name']}")
    
    def refresh_image_list(self):
        """Cập nhật danh sách hình ảnh trong UI"""
        # Clear existing
        for widget in self.image_list_frame.winfo_children():
            widget.destroy()
        
        for i, target in enumerate(self.image_targets):
            row = ctk.CTkFrame(self.image_list_frame)
            row.pack(fill="x", pady=2)
            
            # Thumbnail
            try:
                img = Image.open(target["path"])
                img.thumbnail((40, 40))
                photo = ctk.CTkImage(light_image=img, size=(40, 40))
                img_label = ctk.CTkLabel(row, image=photo, text="")
                img_label.image = photo
                img_label.pack(side="left", padx=5)
            except:
                ctk.CTkLabel(row, text="[IMG]", width=40).pack(side="left", padx=5)
            
            # Info
            info_text = f"{target['name']} | {int(target['confidence']*100)}% | {target['click_type']}"
            ctk.CTkLabel(row, text=info_text, font=("Arial", 10)).pack(side="left", padx=5, expand=True, anchor="w")
            
            # Delete button
            del_btn = ctk.CTkButton(row, text="✕", width=30, height=30, fg_color="red",
                                     command=lambda idx=i: self.remove_image_target(idx))
            del_btn.pack(side="right", padx=5)
    
    def remove_image_target(self, index):
        if 0 <= index < len(self.image_targets):
            removed = self.image_targets.pop(index)
            self.refresh_image_list()
            self.status_var.set(f"Đã xóa: {removed['name']}")
    
    def clear_image_targets(self):
        self.image_targets = []
        self.refresh_image_list()
        self.status_var.set("Đã xóa tất cả hình ảnh mục tiêu")
    
    def find_image_on_screen(self, target):
        """Tìm hình ảnh trên màn hình sử dụng OpenCV"""
        try:
            # Chụp màn hình
            screenshot = np.array(ImageGrab.grab())
            screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
            
            # Đọc template
            template = cv2.imread(target["path"])
            if template is None:
                return None
            
            # Template matching
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= target["confidence"]:
                # Tính tọa độ trung tâm
                h, w = template.shape[:2]
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                return (center_x, center_y, max_val)
            
            return None
        except Exception as e:
            print(f"Error finding image: {e}")
            return None
    
    def test_image_search(self):
        """Test tìm kiếm không click"""
        if not self.image_targets:
            self.status_var.set("Chưa có hình ảnh nào để tìm!")
            return
        
        found_count = 0
        for target in self.image_targets:
            result = self.find_image_on_screen(target)
            if result:
                x, y, conf = result
                self.status_var.set(f"✓ Tìm thấy {target['name']} tại ({x}, {y}) - {int(conf*100)}%")
                found_count += 1
            else:
                self.status_var.set(f"✗ Không tìm thấy {target['name']}")
        
        if found_count == 0:
            self.status_var.set("Không tìm thấy hình ảnh nào trên màn hình!")
    
    def toggle_image_clicking(self):
        if self.is_image_clicking:
            self.stop_image_clicking()
        else:
            self.start_image_clicking()
    
    def start_image_clicking(self):
        if not self.image_targets:
            self.status_var.set("Chưa có hình ảnh nào để tìm!")
            return
        
        self.is_image_clicking = True
        self.image_start_btn.configure(text="⏹ Dừng (F9)", fg_color="red")
        self.status_var.set("Đang quét tìm hình ảnh...")
        
        self.image_click_thread = threading.Thread(target=self.image_click_loop, daemon=True)
        self.image_click_thread.start()
    
    def stop_image_clicking(self):
        self.is_image_clicking = False
        self.image_start_btn.configure(text="▶ Bắt đầu tìm (F9)", fg_color="green")
        self.status_var.set("Đã dừng quét hình ảnh")
    
    def image_click_loop(self):
        """Vòng lặp tìm và click hình ảnh"""
        try:
            interval = int(self.scan_interval.get()) / 1000
            continuous = self.continuous_scan.get()
            
            while self.is_image_clicking:
                for target in self.image_targets:
                    if not self.is_image_clicking:
                        break
                    
                    result = self.find_image_on_screen(target)
                    if result:
                        x, y, conf = result
                        
                        # Perform click
                        click_type = target["click_type"]
                        if click_type == "Trái":
                            pyautogui.click(x, y)
                        elif click_type == "Phải":
                            pyautogui.rightClick(x, y)
                        elif click_type == "Double":
                            pyautogui.doubleClick(x, y)
                        
                        self.root.after(0, lambda t=target, c=conf: 
                            self.status_var.set(f"Clicked {t['name']} ({int(c*100)}%)"))
                        
                        if not continuous:
                            self.root.after(0, self.stop_image_clicking)
                            return
                
                time.sleep(interval)
                
        except Exception as e:
            print(f"Image click error: {e}")
            self.root.after(0, self.stop_image_clicking)

    def setup_record_tab(self):
        frame = self.tab_record
        
        # Info
        info_label = ctk.CTkLabel(frame, text="Ghi lại các thao tác chuột và phát lại tự động",
                                   font=("Arial", 12))
        info_label.pack(pady=10)
        
        # Record button
        self.record_btn = ctk.CTkButton(frame, text="🔴 Bắt đầu ghi (F7)", font=("Arial", 14),
                                         height=40, command=self.toggle_recording, fg_color="red")
        self.record_btn.pack(pady=10, padx=20, fill="x")
        
        # Actions list
        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(list_frame, text="Các thao tác đã ghi:", font=("Arial", 12)).pack(anchor="w", padx=5)
        
        self.actions_textbox = ctk.CTkTextbox(list_frame, height=150)
        self.actions_textbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Playback controls
        playback_frame = ctk.CTkFrame(frame)
        playback_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(playback_frame, text="Số lần lặp:", font=("Arial", 12)).pack(side="left", padx=5)
        self.repeat_count = ctk.CTkEntry(playback_frame, width=70)
        self.repeat_count.pack(side="left", padx=5)
        self.repeat_count.insert(0, "1")
        
        # Speed control
        ctk.CTkLabel(playback_frame, text="Tốc độ:", font=("Arial", 12)).pack(side="left", padx=5)
        self.speed_slider = ctk.CTkSlider(playback_frame, from_=0.5, to=3, width=100)
        self.speed_slider.pack(side="left", padx=5)
        self.speed_slider.set(1)
        
        # Playback button
        self.play_btn = ctk.CTkButton(frame, text="▶ Phát lại (F8)", font=("Arial", 14),
                                       height=40, command=self.toggle_playback, fg_color="green")
        self.play_btn.pack(pady=10, padx=20, fill="x")
        
        # Save/Load buttons
        file_frame = ctk.CTkFrame(frame)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        save_btn = ctk.CTkButton(file_frame, text="💾 Lưu", width=100, command=self.save_actions)
        save_btn.pack(side="left", padx=5, expand=True)
        
        load_btn = ctk.CTkButton(file_frame, text="📂 Tải", width=100, command=self.load_actions)
        load_btn.pack(side="left", padx=5, expand=True)
        
        clear_btn = ctk.CTkButton(file_frame, text="🗑️ Xóa", width=100, command=self.clear_actions, fg_color="gray")
        clear_btn.pack(side="left", padx=5, expand=True)
        
    def setup_settings_tab(self):
        frame = self.tab_settings
        
        # Hotkeys info
        hotkey_frame = ctk.CTkFrame(frame)
        hotkey_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(hotkey_frame, text="⌨️ Phím tắt:", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        
        hotkeys = [
            ("F6", "Bắt đầu/Dừng Auto Click"),
            ("F7", "Bắt đầu/Dừng Ghi"),
            ("F8", "Phát lại thao tác"),
            ("F9", "Bắt đầu/Dừng Tìm hình ảnh"),
            ("F10", "Bắt đầu/Dừng Luồng thao tác"),
            ("ESC", "Dừng tất cả"),
        ]
        
        for key, desc in hotkeys:
            row = ctk.CTkFrame(hotkey_frame)
            row.pack(fill="x", padx=5, pady=2)
            ctk.CTkLabel(row, text=f"{key}:", font=("Arial", 12, "bold"), width=50).pack(side="left")
            ctk.CTkLabel(row, text=desc, font=("Arial", 12)).pack(side="left", padx=10)
        
        # Safety info
        safety_frame = ctk.CTkFrame(frame)
        safety_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(safety_frame, text="⚠️ An toàn:", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        ctk.CTkLabel(safety_frame, text="Di chuyển chuột đến góc trên bên trái màn hình\nđể dừng khẩn cấp (Fail-safe)",
                     font=("Arial", 11), justify="left").pack(anchor="w", padx=5)
        
        # About
        about_frame = ctk.CTkFrame(frame)
        about_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(about_frame, text="ℹ️ Thông tin:", font=("Arial", 14, "bold")).pack(anchor="w", padx=5, pady=5)
        ctk.CTkLabel(about_frame, text="Auto Click Tool v1.0\nCông cụ tự động hóa thao tác Windows",
                     font=("Arial", 11), justify="left").pack(anchor="w", padx=5)
    
    def setup_hotkeys(self):
        keyboard.add_hotkey('F6', self.toggle_clicking)
        keyboard.add_hotkey('F7', self.toggle_recording)
        keyboard.add_hotkey('F8', self.toggle_playback)
        keyboard.add_hotkey('F9', self.toggle_image_clicking)
        keyboard.add_hotkey('F10', self.toggle_workflow)
        keyboard.add_hotkey('ESC', self.stop_all)
    
    def update_mouse_position(self):
        try:
            x, y = pyautogui.position()
            self.current_pos_label.configure(text=f"Vị trí chuột: ({x}, {y})")
        except:
            pass
        self.root.after(100, self.update_mouse_position)
    
    def get_mouse_position(self):
        x, y = pyautogui.position()
        self.pos_x.delete(0, "end")
        self.pos_x.insert(0, str(x))
        self.pos_y.delete(0, "end")
        self.pos_y.insert(0, str(y))

    def toggle_clicking(self):
        if self.is_clicking:
            self.stop_clicking()
        else:
            self.start_clicking()
    
    def start_clicking(self):
        self.is_clicking = True
        self.start_btn.configure(text="⏹ Dừng (F6)", fg_color="red")
        self.status_var.set("Đang click...")
        
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.click_thread.start()
    
    def stop_clicking(self):
        self.is_clicking = False
        self.start_btn.configure(text="▶ Bắt đầu (F6)", fg_color=["#3B8ED0", "#1F6AA5"])
        self.status_var.set("Đã dừng | F6: Bắt đầu/Dừng")
    
    def click_loop(self):
        try:
            interval = int(self.interval_entry.get()) / 1000
            max_clicks = int(self.click_count.get())
            click_type = self.click_type.get()
            use_current = self.use_current_pos.get()
            
            click_count = 0
            while self.is_clicking:
                if max_clicks > 0 and click_count >= max_clicks:
                    self.root.after(0, self.stop_clicking)
                    break
                
                if use_current:
                    x, y = pyautogui.position()
                else:
                    x = int(self.pos_x.get())
                    y = int(self.pos_y.get())
                
                if click_type == "Click trái":
                    pyautogui.click(x, y)
                elif click_type == "Click phải":
                    pyautogui.rightClick(x, y)
                elif click_type == "Double click":
                    pyautogui.doubleClick(x, y)
                
                click_count += 1
                time.sleep(interval)
        except Exception as e:
            print(f"Error: {e}")
            self.root.after(0, self.stop_clicking)
    
    def toggle_recording(self):
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.recorded_actions = []
        self.record_start_time = time.time()
        self.record_btn.configure(text="⏹ Dừng ghi (F7)")
        self.status_var.set("Đang ghi... Click để ghi thao tác")
        
        # Start mouse listener
        self.mouse_listener = mouse.Listener(on_click=self.on_click_record)
        self.mouse_listener.start()
    
    def stop_recording(self):
        self.is_recording = False
        self.record_btn.configure(text="🔴 Bắt đầu ghi (F7)")
        self.status_var.set(f"Đã ghi {len(self.recorded_actions)} thao tác")
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        self.update_actions_display()
    
    def on_click_record(self, x, y, button, pressed):
        if not self.is_recording:
            return False
        
        if pressed:
            elapsed = time.time() - self.record_start_time
            action = {
                "type": "click",
                "x": x,
                "y": y,
                "button": "left" if button == mouse.Button.left else "right",
                "time": elapsed
            }
            self.recorded_actions.append(action)
            self.record_start_time = time.time()
    
    def update_actions_display(self):
        self.actions_textbox.delete("1.0", "end")
        for i, action in enumerate(self.recorded_actions):
            text = f"{i+1}. {action['button'].upper()} click tại ({action['x']}, {action['y']}) - chờ {action['time']:.2f}s\n"
            self.actions_textbox.insert("end", text)
    
    def toggle_playback(self):
        if self.playback_thread and self.playback_thread.is_alive():
            self.is_clicking = False
            return
        
        if not self.recorded_actions:
            self.status_var.set("Không có thao tác nào để phát lại!")
            return
        
        self.playback_thread = threading.Thread(target=self.playback_loop, daemon=True)
        self.playback_thread.start()
    
    def playback_loop(self):
        try:
            repeat = int(self.repeat_count.get())
            speed = self.speed_slider.get()
            
            self.is_clicking = True
            self.play_btn.configure(text="⏹ Dừng phát")
            
            for r in range(repeat):
                if not self.is_clicking:
                    break
                    
                self.status_var.set(f"Đang phát lần {r+1}/{repeat}...")
                
                for action in self.recorded_actions:
                    if not self.is_clicking:
                        break
                    
                    # Wait
                    time.sleep(action["time"] / speed)
                    
                    # Perform action
                    if action["type"] == "click":
                        if action["button"] == "left":
                            pyautogui.click(action["x"], action["y"])
                        else:
                            pyautogui.rightClick(action["x"], action["y"])
            
            self.is_clicking = False
            self.root.after(0, lambda: self.play_btn.configure(text="▶ Phát lại (F8)"))
            self.root.after(0, lambda: self.status_var.set("Phát lại hoàn tất!"))
        except Exception as e:
            print(f"Playback error: {e}")
            self.is_clicking = False

    def save_actions(self):
        if not self.recorded_actions:
            self.status_var.set("Không có thao tác nào để lưu!")
            return
        
        filename = f"actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.recorded_actions, f, indent=2)
        
        self.status_var.set(f"Đã lưu: {filename}")
    
    def load_actions(self):
        # Simple file dialog using tkinter
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            title="Chọn file thao tác",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.recorded_actions = json.load(f)
                self.update_actions_display()
                self.status_var.set(f"Đã tải {len(self.recorded_actions)} thao tác")
            except Exception as e:
                self.status_var.set(f"Lỗi tải file: {e}")
    
    def clear_actions(self):
        self.recorded_actions = []
        self.actions_textbox.delete("1.0", "end")
        self.status_var.set("Đã xóa tất cả thao tác")
    
    def stop_all(self):
        self.is_clicking = False
        self.is_recording = False
        self.is_image_clicking = False
        self.is_workflow_running = False
        
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        self.start_btn.configure(text="▶ Bắt đầu (F6)", fg_color=["#3B8ED0", "#1F6AA5"])
        self.record_btn.configure(text="🔴 Bắt đầu ghi (F7)")
        self.play_btn.configure(text="▶ Phát lại (F8)")
        self.image_start_btn.configure(text="▶ Bắt đầu tìm (F9)", fg_color="green")
        self.workflow_start_btn.configure(text="▶ Chạy luồng (F10)", fg_color="green")
        self.status_var.set("Đã dừng tất cả | F6: Click | F9: Hình ảnh | F10: Luồng | F7: Ghi | F8: Phát")
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = AutoClickTool()
    app.run()
