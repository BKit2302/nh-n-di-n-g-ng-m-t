import tkinter as tk
from tkinter import messagebox
import serial
import serial.tools.list_ports
import threading
import time
from PIL import Image, ImageTk
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
#  CẤU HÌNH GIAO TIẾP SERIAL VỚI ARDUINO
# ============================================================
BAUD_RATE = 9600          # Phải khớp với Serial.begin() trong Arduino
arduino = None            # Đối tượng serial, None = chưa kết nối
serial_lock = threading.Lock()  # Tránh xung đột khi gửi từ nhiều luồng

def tim_cong_arduino():
    """Tự động tìm cổng COM của Arduino (VID=2341 hoặc tên có 'Arduino/CH340/CP210')"""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        if any(k in desc for k in ["arduino", "ch340", "cp210", "usb serial"]) or "2341" in hwid:
            return p.device
    # Fallback: trả về cổng đầu tiên nếu không nhận ra
    return ports[0].device if ports else None

def ket_noi_arduino():
    """Kết nối serial với Arduino; trả về True nếu thành công."""
    global arduino
    cong = tim_cong_arduino()
    if not cong:
        messagebox.showerror("Lỗi kết nối", "Không tìm thấy Arduino!\nHãy cắm USB và thử lại.")
        return False
    try:
        arduino = serial.Serial(cong, BAUD_RATE, timeout=1)
        time.sleep(2)          # Chờ Arduino reset sau khi mở cổng
        return True
    except serial.SerialException as e:
        messagebox.showerror("Lỗi Serial", f"Không thể mở {cong}:\n{e}")
        return False

def gui_lenh(lenh: str):
    """Gửi chuỗi lệnh kết thúc bằng '\\n' tới Arduino (thread-safe)."""
    global arduino
    if arduino and arduino.is_open:
        try:
            with serial_lock:
                arduino.write((lenh + "\n").encode("utf-8"))
        except serial.SerialException:
            pass   # Bỏ qua lỗi tạm thời (rút dây, v.v.)

# ============================================================
#  GIAO THỨC LỆNH (phải khớp với Arduino)
# ============================================================
# ĐÈN ĐƯỜNG (2 LED):   DEN_ON | DEN_OFF | DEN_BLINK
# VÒNG QUAY (servo):   VONG:<0-100>   (0 = dừng, 100 = nhanh nhất)
# NHÀ MA (3 LED):       NHA_ON | NHA_OFF | NHA_BLINK

# ============================================================
#  KHỞI TẠO CỬA SỔ CHÍNH
# ============================================================
root = tk.Tk()
root.title("Hệ Thống Quản Lý Công Viên Ma")
root.geometry("500x450")
root.resizable(False, False)

image_cache = {}

main_canvas = tk.Canvas(root, width=500, height=450, highlightthickness=0)
main_canvas.pack(fill="both", expand=True)

# ============================================================
#  TIỆN ÍCH
# ============================================================
def load_bg(canvas, path, key, w, h):
    try:
        abs_path = os.path.join(BASE_DIR, path)
        img = Image.open(abs_path).resize((w, h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        image_cache[key] = photo
        canvas.create_image(0, 0, image=photo, anchor="nw")
    except Exception as e:
        # Nếu không có ảnh thì tô màu nền tối thay thế
        canvas.configure(bg="#1a0a2e")
        print(f"Không tải được ảnh {path}: {e}")

def tao_nut(parent, text, cmd, **kw):
    defaults = dict(font=("Arial", 11, "bold"), relief="flat",
                    cursor="hand2", padx=8, pady=4)
    defaults.update(kw)
    return tk.Button(parent, text=text, command=cmd, **defaults)

# ============================================================
#  MÀN HÌNH ĐĂNG NHẬP
# ============================================================
entry_taikhoan = None
entry_matkhau  = None

def show_login_screen():
    main_canvas.delete("all")
    load_bg(main_canvas, "bg_main.png", "main", 500, 450)

    main_canvas.create_text(250, 80, text="👻  ĐĂNG NHẬP HỆ THỐNG",
                             font=("Arial", 16, "bold"), fill="white")

    # Tên đăng nhập
    main_canvas.create_text(130, 160, text="Tên đăng nhập:",
                             font=("Arial", 12, "bold"), fill="white", anchor="e")
    global entry_taikhoan
    entry_taikhoan = tk.Entry(root, width=25, font=("Arial", 11), fg="white",
                              bg="#2d1b69", insertbackground="white")
    main_canvas.create_window(270, 160, window=entry_taikhoan)

    # Mật khẩu
    main_canvas.create_text(130, 210, text="Mật khẩu:",
                             font=("Arial", 12, "bold"), fill="white", anchor="e")
    global entry_matkhau
    entry_matkhau = tk.Entry(root, width=25, font=("Arial", 11), show="*", fg="white",
                             bg="#2d1b69", insertbackground="white")
    main_canvas.create_window(270, 210, window=entry_matkhau)

    # Cho phép nhấn Enter để đăng nhập
    entry_matkhau.bind("<Return>", lambda e: dang_nhap())

    btn = tao_nut(root, "Đăng nhập", dang_nhap, bg="lightblue", width=15)
    main_canvas.create_window(250, 280, window=btn)

    # Hiển thị trạng thái kết nối Arduino
    trang_thai = "🟢 Arduino đã kết nối" if (arduino and arduino.is_open) else "🔴 Chưa kết nối Arduino"
    mau = "lightgreen" if (arduino and arduino.is_open) else "#ff6b6b"
    main_canvas.create_text(250, 380, text=trang_thai,
                             font=("Arial", 10), fill=mau)

def dang_nhap():
    tk_val  = entry_taikhoan.get().strip()
    mk_val  = entry_matkhau.get().strip()
    if tk_val == "công minh" and mk_val == "congvienma2005":
        messagebox.showinfo("Thành công", "Chào mừng đến Công Viên Ma! 🎃")
        show_dashboard_screen()
    else:
        messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu!")
        entry_matkhau.delete(0, tk.END)

# ============================================================
#  BẢNG ĐIỀU KHIỂN CHÍNH
# ============================================================
def show_dashboard_screen():
    main_canvas.delete("all")
    load_bg(main_canvas, "bg_bangdieukhien.png", "bangdieukhien", 500, 450)

    main_canvas.create_text(250, 50, text="🎃  BẢNG ĐIỀU KHIỂN",
                             font=("Arial", 17, "bold"), fill="white")

    # Nhãn trạng thái Arduino (cập nhật liên tục)
    lbl_status = tk.Label(root, text="", font=("Arial", 9),
                          bg="#1a0a2e", fg="lightgreen")
    main_canvas.create_window(250, 85, window=lbl_status)
    update_arduino_status(lbl_status)

    # Các nút chức năng
    btns = [
        ("💡  Đèn lối đi",   mo_den_loi_di,  140),
        ("🎡  Vòng quay",    mo_vong_quay,   230),
    ]
    for text, cmd, y in btns:
        b = tao_nut(root, text, cmd,
                    bg="#2d1b69", fg="white", width=22, height=2)
        main_canvas.create_window(250, y, window=b)

    # Nút đăng xuất
    b_out = tao_nut(root, "Đăng xuất", show_login_screen,
                    bg="#5c0a0a", fg="white", width=12)
    main_canvas.create_window(250, 405, window=b_out)

def update_arduino_status(label):
    """Cập nhật nhãn trạng thái Arduino mỗi 2 giây."""
    if arduino and arduino.is_open:
        label.config(text="🟢 Arduino đang kết nối", fg="lightgreen")
    else:
        label.config(text="🔴 Arduino chưa kết nối", fg="#ff6b6b")
    try:
        root.after(2000, lambda: update_arduino_status(label))
    except tk.TclError:
        pass   # Cửa sổ đã đóng

# ============================================================
#  CỬA SỔ CON — ĐÈN LỐI ĐI
# ============================================================
def mo_den_loi_di():
    win = tk.Toplevel(root)
    win.title("Đèn lối đi")
    win.geometry("300x260")
    win.resizable(False, False)

    cv = tk.Canvas(win, width=300, height=260, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    load_bg(cv, "bg_denloidi.png", "denloidi", 300, 260)

    cv.create_text(150, 35, text="💡  Điều khiển Đèn lối đi",
                   font=("Arial", 12, "bold"), fill="white")

    # Nhãn trạng thái hiện tại
    lbl = tk.Label(win, text="Trạng thái: ---",
                   font=("Arial", 10), bg="#1a0a2e", fg="white")
    cv.create_window(150, 65, window=lbl)

    def bat():
        gui_lenh("DEN_ON")
        lbl.config(text="Trạng thái: BẬT 🟡")

    def tat():
        gui_lenh("DEN_OFF")
        lbl.config(text="Trạng thái: TẮT ⚫")

    def nhap_nhay():
        gui_lenh("DEN_BLINK")
        lbl.config(text="Trạng thái: NHẤP NHÁY ✨")

    for (txt, fn, y, col) in [
        ("Bật",         bat,       105, "#f0c040"),
        ("Tắt",         tat,       165, "#555555"),
        ("Nhấp nháy",   nhap_nhay, 220, "#4080ff"),
    ]:
        b = tao_nut(win, txt, fn, bg=col, fg="white", width=18)
        cv.create_window(150, y, window=b)

# ============================================================
#  CỬA SỔ CON — VÒNG QUAY
# ============================================================
def mo_vong_quay():
    win = tk.Toplevel(root)
    win.title("Vòng quay")
    win.geometry("360x230")
    win.resizable(False, False)

    cv = tk.Canvas(win, width=360, height=230, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    load_bg(cv, "bg_vongquay.png", "vongquay", 360, 230)

    cv.create_text(180, 35, text="🎡  Điều khiển Vòng quay",
                   font=("Arial", 12, "bold"), fill="white")

    cv.create_text(50,  105, text="Dừng",  font=("Arial", 10, "bold"), fill="red")
    cv.create_text(310, 105, text="Nhanh", font=("Arial", 10, "bold"), fill="#00FF00")

    toc_do_var = tk.IntVar(value=0)

    def on_change(val):
        """Gửi lệnh VONG:<tốc độ> mỗi khi thanh trượt thay đổi."""
        gui_lenh(f"VONG:{val}")
        lbl_toc_do.config(text=f"Tốc độ: {val}%")

    thanh_truot = tk.Scale(
        win, from_=0, to=100, orient=tk.HORIZONTAL,
        variable=toc_do_var, command=on_change,
        length=220, sliderlength=20,
        bg="#2d1b69", fg="white", troughcolor="#555",
        highlightthickness=0
    )
    cv.create_window(180, 130, window=thanh_truot)

    lbl_toc_do = tk.Label(win, text="Tốc độ: 0%",
                          font=("Arial", 10), bg="#1a0a2e", fg="white")
    cv.create_window(180, 185, window=lbl_toc_do)

    # Nút dừng khẩn
    def dung_khan():
        toc_do_var.set(0)
        on_change(0)

    b_dung = tao_nut(win, "⛔ DỪNG KHẨN", dung_khan,
                     bg="#cc0000", fg="white", width=14)
    cv.create_window(180, 210, window=b_dung)

# ============================================================
#  CỬA SỔ CON — NHÀ MA
# ============================================================
def mo_nha_ma():
    win = tk.Toplevel(root)
    win.title("Nhà ma")
    win.geometry("300x260")
    win.resizable(False, False)

    cv = tk.Canvas(win, width=300, height=260, highlightthickness=0)
    cv.pack(fill="both", expand=True)
    load_bg(cv, "bg_nhama.png", "nhama", 300, 260)

    cv.create_text(150, 35, text="🏚  Hệ thống Đèn nhà ma",
                   font=("Arial", 12, "bold"), fill="white")

    lbl = tk.Label(win, text="Trạng thái: ---",
                   font=("Arial", 10), bg="#1a0a2e", fg="white")
    cv.create_window(150, 65, window=lbl)

    def bat():
        gui_lenh("NHA_ON")
        lbl.config(text="Trạng thái: BẬT 🔴")

    def tat():
        gui_lenh("NHA_OFF")
        lbl.config(text="Trạng thái: TẮT ⚫")

    def nhap_nhay():
        gui_lenh("NHA_BLINK")
        lbl.config(text="Trạng thái: NHẤP NHÁY 👻")

    for (txt, fn, y, col) in [
        ("Bật",         bat,       105, "#cc2222"),
        ("Tắt",         tat,       165, "#333333"),
        ("Nhấp nháy",   nhap_nhay, 220, "#993399"),
    ]:
        b = tao_nut(win, txt, fn, bg=col, fg="white", width=18)
        cv.create_window(150, y, window=b)

# ============================================================
#  KHỞI ĐỘNG ỨNG DỤNG
# ============================================================
def khoi_dong():
    # Thử kết nối Arduino ngay khi mở app (không bắt buộc — vẫn dùng được nếu chưa cắm)
    ket_noi_arduino()
    show_login_screen()

def dong_ung_dung():
    global arduino
    if arduino and arduino.is_open:
        gui_lenh("DEN_OFF")   # Tắt an toàn trước khi đóng
        gui_lenh("NHA_OFF")
        gui_lenh("VONG:0")
        time.sleep(0.3)
        arduino.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", dong_ung_dung)
khoi_dong()
root.mainloop()
