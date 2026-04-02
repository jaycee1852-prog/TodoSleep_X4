import sys
import os
import io
import json
import calendar
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests as req

# ── 경로 설정 ─────────────────────────────────────────────
if hasattr(sys, "_MEIPASS"):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

BMP_FILENAME     = os.path.join(APP_DIR, "todo.bmp")
CUSTOM_FONT_PATH = os.path.join(APP_DIR, "custom_font.ttf")
SETTINGS_FILE    = os.path.join(APP_DIR, "settings.json")

IMG_W, IMG_H = 480, 800

# ── 설정 저장/불러오기 ────────────────────────────────────
def load_settings():
    try:
        return json.load(open(SETTINGS_FILE, encoding="utf-8"))
    except:
        return {"ip": ""}

def save_settings(data):
    json.dump(data, open(SETTINGS_FILE, "w", encoding="utf-8"), ensure_ascii=False)

# ── BMP 생성 ──────────────────────────────────────────────
def resolve_font():
    if os.path.exists(CUSTOM_FONT_PATH):
        return CUSTOM_FONT_PATH
    for c in ["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf",
              "C:/Windows/Fonts/gulim.ttc", "C:/Windows/Fonts/NanumGothic.ttf"]:
        if os.path.exists(c):
            return c
    return None

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return None

def create_bmp(todo_list, font_scale=0, title="TO-DO LIST"):
    fp = resolve_font()
    if fp:
        title_font = get_font(fp, 38 + font_scale)
        item_font  = get_font(fp, 26 + font_scale)
        sub_font   = get_font(fp, 22 + font_scale)
        date_font  = get_font(fp, 18 + font_scale)
    else:
        title_font = item_font = sub_font = date_font = ImageFont.load_default()

    img  = Image.new("RGB", (IMG_W, IMG_H), "white")
    draw = ImageDraw.Draw(img)
    PAD  = 24

    y = 20
    title_text = title
    try:
        bb = draw.textbbox((0, 0), title_text, font=title_font)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
    except:
        tw, th = draw.textsize(title_text, font=title_font)
    draw.text(((IMG_W-tw)//2, y), title_text, fill="black", font=title_font)
    y += th + 28

    now = datetime.now().strftime("%Y년 %m월 %d일  %H:%M")
    try:
        db = draw.textbbox((0,0), now, font=date_font)
        dw = db[2]-db[0]
        dh = db[3]-db[1]
    except:
        dw, dh = draw.textsize(now, font=date_font)
    draw.text((IMG_W-PAD-dw, y), now, fill="black", font=date_font)
    y += dh + 12
    draw.line([(PAD, y), (IMG_W-PAD, y)], fill="#888888", width=1)
    y += 14

    ITEM_H, SUB_H, BOX, SUB_PAD = 44, 36, 18, 32
    # 글씨 크기 증가분에 맞춰 줄 높이를 넉넉하게 확보 (겹침 방지)
    if font_scale != 0:
        ITEM_H += int(font_scale * 1.4)
        SUB_H += int(font_scale * 1.4)

    def get_wrapped_text(text, font, max_width):
        lines = []
        if not text: return lines
        current_line = ""
        for char in text:
            test_line = current_line + char
            try:
                bb = draw.textbbox((0, 0), test_line, font=font)
                w = bb[2] - bb[0]
            except:
                w, _ = draw.textsize(test_line, font=font)
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    for item in todo_list[:12]:
        d_text = ""
        dw2 = 0
        if item.get("date"):
            d_text = item["date"]
            # 이미지: 연도 제외 (MM.DD)
            if "~" in d_text:
                parts = d_text.split("~")
                new_parts = []
                for p in parts:
                    p = p.strip()
                    if len(p) > 5 and p[4] == '-':
                        new_parts.append(p[5:])
                    else:
                        new_parts.append(p)
                d_text = "~".join(new_parts)
            elif len(d_text) > 5 and d_text[4] == '-':
                d_text = d_text[5:]
            d_text = d_text.replace("-", ".")
            try:
                dbb = draw.textbbox((0,0), d_text, font=date_font)
                dw2 = dbb[2]-dbb[0]
            except:
                dw2, _ = draw.textsize(d_text, font=date_font)

        tx = PAD + BOX + 12
        date_area = (dw2 + 10) if d_text else 0
        max_text_width = IMG_W - tx - PAD - date_area
        
        lines = get_wrapped_text(item["text"], item_font, max_text_width)
        if not lines: lines = [""]

        try:
            bb = draw.textbbox((0,0), "Hg", font=item_font)
            line_h = bb[3] - bb[1]
            line_offset = bb[1]
        except:
            _, line_h = draw.textsize("Hg", font=item_font)
            line_offset = 0
            
        line_spacing = 4
        text_block_h = len(lines) * line_h + (len(lines) - 1) * line_spacing
        this_item_h = max(ITEM_H, text_block_h + 24)

        if y + this_item_h > IMG_H - 10:
            break

        draw.rectangle([0, y, IMG_W, y+this_item_h-1], fill="white")
        bx = y + (this_item_h - BOX) // 2
        draw.rectangle([PAD, bx, PAD+BOX, bx+BOX], outline="#333333", width=2)

        text_y_start = y + (this_item_h - text_block_h) // 2
        for i, line in enumerate(lines):
            ly = text_y_start + i * (line_h + line_spacing)
            draw.text((tx, ly - line_offset), line, fill="#1a1a1a", font=item_font)

        if d_text:
            try:
                dbb = draw.textbbox((0,0), d_text, font=date_font)
                dh2 = dbb[3]-dbb[1]
                dy2 = y + (this_item_h - dh2) // 2 - dbb[1]
            except:
                _, dh2 = draw.textsize(d_text, font=date_font)
                dy2 = y + (this_item_h - dh2) // 2
            draw.text((IMG_W-PAD-dw2-4, dy2), d_text, fill="black", font=date_font)

        y += this_item_h

        for sub in item.get("sub", []):
            sx = PAD + SUB_PAD + 18
            max_sub_width = IMG_W - sx - PAD
            
            sub_lines = get_wrapped_text(sub, sub_font, max_sub_width)
            if not sub_lines: sub_lines = [""]

            try:
                sb = draw.textbbox((0,0), "Hg", font=sub_font)
                s_line_h = sb[3] - sb[1]
                s_line_offset = sb[1]
            except:
                _, s_line_h = draw.textsize("Hg", font=sub_font)
                s_line_offset = 0
            
            s_line_spacing = 4
            sub_text_block_h = len(sub_lines) * s_line_h + (len(sub_lines) - 1) * s_line_spacing
            this_sub_h = max(SUB_H, sub_text_block_h + 16)

            if y + this_sub_h > IMG_H - 10:
                break

            draw.rectangle([0, y, IMG_W, y+this_sub_h-1], fill="white")
            draw.line([(PAD+SUB_PAD-6, y+4), (PAD+SUB_PAD-6, y+this_sub_h-4)], fill="black", width=2)
            sy2 = y + (this_sub_h-12)//2
            draw.ellipse([PAD+SUB_PAD, sy2, PAD+SUB_PAD+12, sy2+12], outline="black", width=1)
            
            sub_text_y_start = y + (this_sub_h - sub_text_block_h) // 2
            for i, s_line in enumerate(sub_lines):
                sly = sub_text_y_start + i * (s_line_h + s_line_spacing)
                draw.text((sx, sly - s_line_offset), s_line, fill="black", font=sub_font)
            
            y += this_sub_h

        draw.line([(PAD, y), (IMG_W-PAD, y)], fill="#888888", width=1)
        y += 3

    img.save(BMP_FILENAME, format="BMP")
    return img

def send_to_x4(ip, todo_list, font_scale=0, title="TO-DO LIST"):
    create_bmp(todo_list, font_scale, title)
    url = f"http://{ip}/upload"
    try:
        with open(BMP_FILENAME, "rb") as f:
            req.post(url, files={"file": ("todo.bmp", f, "image/bmp")},
                     data={"path": "sleep"}, timeout=10)
        return True, "X4 전송 완료! (sleep 폴더)"
    except req.exceptions.ConnectionError:
        return False, f"연결 실패. IP({ip})와 Wi-Fi를 확인해주세요."
    except Exception as e:
        return False, f"오류: {str(e)}"

def check_connection(ip):
    try:
        req.get(f"http://{ip}/", timeout=4)
        return True, f"연결 성공! ({ip})"
    except req.exceptions.ConnectionError:
        return False, f"연결 실패. IP({ip})와 Wi-Fi를 확인해주세요."
    except req.exceptions.Timeout:
        return False, "응답 없음. X4가 켜져 있는지 확인해주세요."
    except Exception as e:
        return False, f"오류: {str(e)}"

# ── 달력 팝업 ─────────────────────────────────────────────
class CalendarDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback, init_date=None, color_theme=None):
        super().__init__(parent)
        self.callback = callback
        self.title("날짜 선택")
        self.geometry("280x320")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        
        try:
            x = parent.winfo_x() + (parent.winfo_width()//2) - 140
            y = parent.winfo_y() + (parent.winfo_height()//2) - 160
            self.geometry(f"+{x}+{y}")
        except: pass

        self.C = color_theme if color_theme else {"bg": "#1a1a2e", "text": "#e2e8f0", "blue": "#2b6cb0"}
        self.configure(fg_color=self.C["bg"])

        dt = datetime.now()
        self.selection_mode = tk.StringVar(value="날짜")
        self.start_date = None
        self.year, self.month = dt.year, dt.month
        if init_date and "-" in init_date:
            try:
                parts = init_date.split("-")
                self.year, self.month = int(parts[0]), int(parts[1])
            except: pass
        self._build_calendar()

    def _build_calendar(self):
        for w in self.winfo_children(): w.destroy()
        
        # 모드 선택 (날짜 / 기간)
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(10, 0), padx=10)
        mode_btn = ctk.CTkSegmentedButton(mode_frame, values=["날짜", "기간"],
                                          variable=self.selection_mode, command=self._reset_selection)
        mode_btn.pack(fill="x")

        h_frame = ctk.CTkFrame(self, fg_color="transparent")
        h_frame.pack(fill="x", pady=10)
        ctk.CTkButton(h_frame, text="<", width=30, fg_color="transparent", text_color=self.C["text"], hover_color=self.C["blue"], command=lambda: self._change_month(-1)).pack(side="left", padx=10)
        ctk.CTkLabel(h_frame, text=f"{self.year}년 {self.month}월", font=("맑은 고딕", 14, "bold"), text_color=self.C["text"]).pack(side="left", expand=True)
        ctk.CTkButton(h_frame, text=">", width=30, fg_color="transparent", text_color=self.C["text"], hover_color=self.C["blue"], command=lambda: self._change_month(1)).pack(side="right", padx=10)

        d_frame = ctk.CTkFrame(self, fg_color="transparent")
        d_frame.pack(fill="both", expand=True, padx=10, pady=5)
        for i, w in enumerate(["일", "월", "화", "수", "목", "금", "토"]):
            color = "#fc8181" if i == 0 else ("#63b3ed" if i == 6 else self.C["text"])
            ctk.CTkLabel(d_frame, text=w, font=("맑은 고딕", 10, "bold"), text_color=color, width=35).grid(row=0, column=i, pady=5)

        today = datetime.now()
        for r, week in enumerate(calendar.monthcalendar(self.year, self.month)):
            for c, day in enumerate(week):
                if day == 0: continue
                
                curr_date = f"{self.year}-{self.month:02d}-{day:02d}"
                fg = "transparent"
                txt_col = self.C["text"]
                border_w = 0
                border_col = None

                if today.year == self.year and today.month == self.month and today.day == day:
                    border_w = 1
                    border_col = self.C["ok"]

                if self.selection_mode.get() == "기간" and self.start_date == curr_date:
                    fg = self.C["blue"]
                    txt_col = "white"

                ctk.CTkButton(d_frame, text=str(day), width=35, height=30, 
                              fg_color=fg, text_color=txt_col, 
                              border_width=border_w, border_color=border_col,
                              hover_color=self.C["blue"], corner_radius=5, 
                              command=lambda d=day: self._on_select(d)).grid(row=r+1, column=c, pady=2)

    def _reset_selection(self, _=None):
        self.start_date = None
        self.title("날짜 선택")

    def _change_month(self, delta):
        self.month += delta
        if self.month < 1: self.month = 12; self.year -= 1
        elif self.month > 12: self.month = 1; self.year += 1
        self._build_calendar()

    def _on_select(self, day):
        sel_date = f"{self.year}-{self.month:02d}-{day:02d}"
        
        if self.selection_mode.get() == "날짜":
            self.callback(sel_date)
            self.destroy()
        else:
            # 기간 선택 로직
            if not self.start_date:
                self.start_date = sel_date
                self.title(f"시작: {sel_date} (종료일 선택)")
                self._build_calendar()
            else:
                # 날짜 정렬 (시작~종료)
                d1, d2 = sorted([self.start_date, sel_date])
                self.callback(f"{d1}~{d2}")
                self.destroy()

# ── GUI (CustomTkinter) ───────────────────────────────────
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("X4 To-Do 슬립화면")
        self.geometry("1000x700")
        self.minsize(800, 560)
        self.configure(fg_color="#1a1a2e")
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.settings  = load_settings()
        self.todos     = []        # [{"text": str, "sub": [str], "open": bool}]
        self.todos     = self.settings.get("todos", [])
        self.font_scale = self.settings.get("font_scale", 0)
        self.title_text = self.settings.get("title", "TO-DO LIST")
        
        # 기존 데이터에 created_at이 없으면 추가 (정렬용)
        for item in self.todos:
            if "created_at" not in item:
                item["created_at"] = time.time()

        self.preview_after = None
        self.editing_index = None

        self._build_ui()
        
        # 저장된 정렬 상태가 있다면 적용 (여기서는 기본값으로 초기화)
        self._sort_list()
        self._load_font_status()
        self._refresh_preview_delayed()

    def _save_todos(self):
        self.settings["todos"] = self.todos
        save_settings(self.settings)

    # ── UI 구성 ───────────────────────────────────────────
    def _build_ui(self):
        # 색상 팔레트
        C = self.C = {
            "bg":      "#1a1a2e",
            "panel":   "#16213e",
            "input":   "#0d1b2a",
            "border":  "#2d3748",
            "blue":    "#2b6cb0",
            "green":   "#276749",
            "text":    "#e2e8f0",
            "muted":   "#718096",
            "ok":      "#68d391",
            "err":     "#fc8181",
        }

        # 전체 레이아웃
        main = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        main.pack(fill="both", expand=True, padx=16, pady=16)
        main.columnconfigure(0, weight=0) # Left: Fixed
        main.columnconfigure(1, weight=1) # Middle: Expand
        main.columnconfigure(2, weight=0) # Right: Fixed
        main.rowconfigure(0, weight=1)

        # ── 1. 왼쪽 패널 ──
        left_panel = ctk.CTkFrame(main, fg_color=C["panel"], corner_radius=15, width=320,
                                  border_width=1, border_color=C["border"])
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_panel.pack_propagate(False)

        lp = ctk.CTkFrame(left_panel, fg_color="transparent")
        lp.pack(fill="both", expand=True, padx=16, pady=16)

        # 헤더
        ctk.CTkLabel(lp, text="☑  X4 To-Do 슬립화면", text_color=C["text"],
                     font=("맑은 고딕", 20, "bold")).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(lp, text="Xteink X4 연동", fg_color="#0f3460", text_color="#63b3ed",
                     font=("맑은 고딕", 12), corner_radius=6).pack(anchor="w", pady=(0, 16))

        self._sep(lp)

        # IP 설정
        self._label(lp, "📡  X4 IP 주소")

        self.ip_var = tk.StringVar(value=self.settings.get("ip",""))
        self.ip_var.trace_add("write", lambda *_: self._save_ip())
        ip_entry = ctk.CTkEntry(lp, textvariable=self.ip_var,
                                fg_color=C["input"], text_color=C["text"], border_width=0,
                                font=("맑은 고딕", 12), height=35, corner_radius=8)
        ip_entry.pack(fill="x", pady=(4, 8))
        
        btn_row = ctk.CTkFrame(lp, fg_color="transparent")
        btn_row.pack(fill="x")
        self.btn_check = self._btn(btn_row, "연결 확인", self._check_conn, C["blue"])
        self.btn_check.pack(side="left", fill="x", expand=True)
        
        self.conn_lbl = ctk.CTkLabel(lp, text="", text_color=C["muted"], font=("맑은 고딕", 11))
        self.conn_lbl.pack(anchor="w", pady=(6, 0))

        self._sep(lp)

        # 제목 설정
        self._label(lp, "🏷️  제목 설정")
        self.title_var = tk.StringVar(value=self.title_text)
        self.title_var.trace_add("write", lambda *_: self._save_title())
        title_entry = ctk.CTkEntry(lp, textvariable=self.title_var,
                                   fg_color=C["input"], text_color=C["text"], border_width=0,
                                   font=("맑은 고딕", 12), height=35, corner_radius=8)
        title_entry.pack(fill="x", pady=(4, 8))

        self._sep(lp)

        # 폰트 설정
        self._label(lp, "🔤  글꼴 설정")
        font_box = ctk.CTkFrame(lp, fg_color=C["input"], corner_radius=10, border_width=1, border_color=C["border"])
        font_box.pack(fill="x", pady=(4, 8))
        
        f_top = ctk.CTkFrame(font_box, fg_color="transparent")
        f_top.pack(fill="x", padx=10, pady=8)
        self.font_dot = ctk.CTkLabel(f_top, text="●", text_color=C["muted"])
        self.font_dot.pack(side="left")
        self.font_name_lbl = ctk.CTkLabel(f_top, text="기본 폰트", text_color=C["muted"], font=("맑은 고딕", 11))
        self.font_name_lbl.pack(side="left", padx=6)

        f_btns = ctk.CTkFrame(font_box, fg_color="transparent")
        f_btns.pack(fill="x", padx=10, pady=(0, 8))
        self._btn(f_btns, "변경", self._upload_font, C["border"], width=6).pack(side="left", padx=(0,4))
        self._btn(f_btns, "초기화", self._reset_font, C["border"], width=6).pack(side="left")

        f_size = ctk.CTkFrame(font_box, fg_color="transparent")
        f_size.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(f_size, text="크기 조절", font=("맑은 고딕", 11), text_color=C["muted"]).pack(side="left")
        
        # 버튼 간격을 줄이기 위해 별도 컨테이너 사용
        fs_box = ctk.CTkFrame(f_size, fg_color="transparent")
        fs_box.pack(side="right")
        
        ctk.CTkButton(fs_box, text="-", fg_color=C["border"], text_color=C["text"],
                      font=("맑은 고딕", 12, "bold"), hover_color=C["input"],
                      command=self._decrease_font, width=28, height=28, corner_radius=6).pack(side="left", padx=0)

        self.size_lbl = ctk.CTkLabel(fs_box, text=f"{self.font_scale:+}", font=("맑은 고딕", 12, "bold"), width=36, text_color=C["text"])
        self.size_lbl.pack(side="left", padx=0)
        
        ctk.CTkButton(fs_box, text="+", fg_color=C["border"], text_color=C["text"],
                      font=("맑은 고딕", 12, "bold"), hover_color=C["input"],
                      command=self._increase_font, width=28, height=28, corner_radius=6).pack(side="left", padx=0)

        self.font_msg = ctk.CTkLabel(lp, text="", text_color=C["ok"], font=("맑은 고딕", 10))
        self.font_msg.pack(anchor="w")

        self._sep(lp)

        # 전송 버튼 (왼쪽 하단)
        ctk.CTkLabel(lp, text="").pack(fill="y", expand=True) # Spacer
        
        self.status_lbl = ctk.CTkLabel(lp, text="", text_color=C["ok"], font=("맑은 고딕", 11))
        self.status_lbl.pack(pady=(0, 6))
        
        self.btn_send = ctk.CTkButton(lp, text="📲  X4로 전송하기", fg_color=C["blue"], text_color="white",
                                      font=("맑은 고딕", 14, "bold"), height=45, corner_radius=10,
                                      hover_color="#2c5282", command=self._send)
        self.btn_send.pack(fill="x")

        # ── 2. 가운데 패널 ──
        mid_panel = ctk.CTkFrame(main, fg_color=C["panel"], corner_radius=15,
                                 border_width=1, border_color=C["border"])
        mid_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        mid_panel.columnconfigure(0, weight=1)
        mid_panel.rowconfigure(1, weight=0)
        mid_panel.rowconfigure(2, weight=1)

        # 할일 입력 (상단 고정)
        input_frame = ctk.CTkFrame(mid_panel, fg_color="transparent")
        input_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 0))
        input_frame.columnconfigure(0, weight=1)
        
        self._label(input_frame, "📝  할 일 추가")
        
        add_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        add_row.pack(fill="x", pady=(4,0))
        add_row.columnconfigure(1, weight=1)

        self.new_date_var = tk.StringVar(value="날짜")
        date_btn = ctk.CTkButton(add_row, textvariable=self.new_date_var,
                                 fg_color=C["input"], text_color=C["text"],
                                 font=("맑은 고딕", 11), width=100, height=35, corner_radius=8,
                                 hover_color=C["border"],
                                 command=lambda: self._open_calendar(self.new_date_var))
        date_btn.grid(row=0, column=0, sticky="ns", padx=(0,8))

        self.new_item_var = tk.StringVar()
        entry = ctk.CTkEntry(add_row, textvariable=self.new_item_var,
                             fg_color=C["input"], text_color=C["text"], border_width=0,
                             font=("맑은 고딕", 13), height=35, corner_radius=8)
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", lambda e: self._add_item())

        self._btn(add_row, "추가", self._add_item, C["blue"], width=6).grid(
            row=0, column=2, padx=(8,0))

        # 정렬 및 도구 모음
        tool_frame = ctk.CTkFrame(mid_panel, fg_color="transparent")
        tool_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 4))
        
        self.sort_var = tk.StringVar(value="등록순")
        sort_menu = ctk.CTkOptionMenu(tool_frame, values=["등록순", "날짜순", "이름순"],
                                      variable=self.sort_var, command=self._sort_list,
                                      width=100, height=28, font=("맑은 고딕", 11),
                                      fg_color=C["input"], button_color=C["border"], text_color=C["text"])

        del_all_btn = self._btn(tool_frame, "전체 삭제", self._clear_all, C["err"], width=80)
        del_all_btn.configure(height=28, fg_color="transparent", border_width=1, border_color=C["err"], text_color=C["err"])
        del_all_btn.pack(side="right")
        sort_menu.pack(side="right", padx=(0, 8))

        # 리스트 (스크롤 영역)
        self.list_frame = ctk.CTkScrollableFrame(mid_panel, fg_color="transparent")
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # ── 3. 오른쪽 패널 ──
        right_panel = ctk.CTkFrame(main, fg_color=C["panel"], corner_radius=15, width=260,
                                   border_width=1, border_color=C["border"])
        right_panel.grid(row=0, column=2, sticky="n")

        rp = ctk.CTkFrame(right_panel, fg_color="transparent")
        rp.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(rp, text="🖼  미리보기", text_color=C["muted"],
                     font=("맑은 고딕", 12, "bold")).pack(anchor="w", pady=(0,10))

        self.preview_lbl = ctk.CTkLabel(rp, text="", fg_color=C["input"], corner_radius=10)
        self.preview_lbl.pack(fill="both", expand=True)

        self._btn(rp, "새로고침", self._refresh_preview_now, C["border"]).pack(fill="x", pady=(10,0))

    # ── 유틸 위젯 ─────────────────────────────────────────
    def _sep(self, parent):
        ctk.CTkFrame(parent, fg_color=self.C["border"], height=2).pack(fill="x", pady=8)

    def _label(self, parent, text):
        ctk.CTkLabel(parent, text=text, text_color=self.C["muted"],
                     font=("맑은 고딕", 12, "bold")).pack(anchor="w", pady=(6,4))

    def _btn(self, parent, text, cmd, bg, width=None):
        kw = dict(text=text, fg_color=bg, text_color=self.C["text"],
                  font=("맑은 고딕", 11), hover_color=self.C["border"],
                  command=cmd, height=32, corner_radius=8)
        if width:
            kw["width"] = width
        return ctk.CTkButton(parent, **kw)

    def _open_calendar(self, var):
        CalendarDialog(self, lambda d: var.set(d), init_date=var.get(), color_theme=self.C)

    # ── 설정 및 저장 ──────────────────────────────────────
    def _save_ip(self):
        self.settings["ip"] = self.ip_var.get().strip()
        save_settings(self.settings)

    def _save_title(self):
        self.title_text = self.title_var.get()
        self.settings["title"] = self.title_text
        save_settings(self.settings)
        self._refresh_preview_delayed()

    def _check_conn(self):
        ip = self.ip_var.get().strip()
        if not ip:
            self.conn_lbl.configure(text="IP를 먼저 입력해주세요.", text_color=self.C["err"])
            return
        self.btn_check.configure(state="disabled", text="확인 중...")
        self.conn_lbl.configure(text="연결 확인 중...", text_color=self.C["muted"])

        def run():
            ok, msg = check_connection(ip)
            self.after(0, lambda: self._set_conn(ok, msg))
        threading.Thread(target=run, daemon=True).start()

    def _set_conn(self, ok, msg):
        color = self.C["ok"] if ok else self.C["err"]
        dot   = "●  " if ok else "●  "
        self.conn_lbl.configure(text=dot + msg, text_color=color)
        self.btn_check.configure(state="normal", text="연결 확인")

    # ── 폰트 ──────────────────────────────────────────────
    def _load_font_status(self):
        if os.path.exists(CUSTOM_FONT_PATH):
            self.font_dot.configure(text_color=self.C["ok"])
            self.font_name_lbl.configure(text="커스텀 폰트 적용됨", text_color=self.C["ok"])
        else:
            self.font_dot.configure(text_color=self.C["muted"])
            self.font_name_lbl.configure(text="기본 폰트 (맑은 고딕)", text_color=self.C["muted"])

    def _upload_font(self):
        path = filedialog.askopenfilename(
            title="폰트 파일 선택",
            filetypes=[("폰트 파일", "*.ttf *.otf *.ttc"), ("모든 파일", "*.*")])
        if not path:
            return
        try:
            ImageFont.truetype(path, 20)  # 유효성 검사
            import shutil
            shutil.copy2(path, CUSTOM_FONT_PATH)
            self.font_msg.configure(text=f"폰트 적용 완료! ({os.path.basename(path)})",
                                    text_color=self.C["ok"])
            self._load_font_status()
            self._refresh_preview_now()
        except Exception as e:
            self.font_msg.configure(text=f"유효하지 않은 폰트 파일이에요.", text_color=self.C["err"])

    def _reset_font(self):
        if os.path.exists(CUSTOM_FONT_PATH):
            os.remove(CUSTOM_FONT_PATH)
        self.font_msg.configure(text="기본 폰트로 되돌렸어요.", text_color=self.C["ok"])
        self._load_font_status()
        self._refresh_preview_now()

    def _increase_font(self):
        self.font_scale += 2
        self.size_lbl.configure(text=f"{self.font_scale:+}")
        self.settings["font_scale"] = self.font_scale
        save_settings(self.settings)
        self._refresh_preview_now()

    def _decrease_font(self):
        self.font_scale -= 2
        self.size_lbl.configure(text=f"{self.font_scale:+}")
        self.settings["font_scale"] = self.font_scale
        save_settings(self.settings)
        self._refresh_preview_now()

    # ── 할 일 목록 ────────────────────────────────────────
    def _add_item(self):
        text = self.new_item_var.get().strip()
        date = self.new_date_var.get()
        if date == "날짜": date = ""
        if not text or len(self.todos) >= 12:
            return
        self.todos.append({"text": text, "sub": [], "open": False, "date": date, "created_at": time.time()})
        self.new_item_var.set("")
        self.new_date_var.set("날짜")
        self._save_todos()
        self._sort_list()
        self._render_list()
        self._refresh_preview_delayed()

    def _remove_item(self, i):
        self.todos.pop(i)
        self._save_todos()
        self._render_list()
        self._refresh_preview_delayed()

    def _toggle_sub(self, i):
        self.todos[i]["open"] = not self.todos[i]["open"]
        self._save_todos() # 상태 저장
        self._render_list()

    def _add_sub(self, i, var):
        text = var.get().strip()
        if not text or len(self.todos[i]["sub"]) >= 8:
            return
        self.todos[i]["sub"].append(text)
        var.set("")
        self._save_todos()
        self._render_list()
        self._refresh_preview_delayed()

    def _remove_sub(self, i, j):
        self.todos[i]["sub"].pop(j)
        self._save_todos()
        self._render_list()
        self._refresh_preview_delayed()

    def _toggle_pin(self, i):
        self.todos[i]["pinned"] = not self.todos[i].get("pinned", False)
        self._save_todos()
        self._sort_list()

    def _sort_list(self, _=None):
        mode = self.sort_var.get()
        if mode == "등록순":
            self.todos.sort(key=lambda x: x.get("created_at", 0))
        elif mode == "날짜순":
            # 날짜가 없는 경우 뒤로 가도록 처리 ('~'는 문자열 비교에서 뒤쪽임)
            self.todos.sort(key=lambda x: x.get("date", "") if x.get("date") else "9999-99-99")
        elif mode == "이름순":
            self.todos.sort(key=lambda x: x["text"])
        self.todos.sort(key=lambda x: not x.get("pinned", False))
        self._render_list()
        self._refresh_preview_delayed()

    def _clear_all(self):
        if not self.todos: return
        if messagebox.askyesno("전체 삭제", "목록을 전부 삭제하시겠습니까?"):
            self.todos = []
            self._save_todos()
            self._render_list()
            self._refresh_preview_delayed()

    def _render_list(self):
        C = self.C
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.todos:
            ctk.CTkLabel(self.list_frame, text="할 일을 추가해보세요!",
                         text_color=C["muted"], font=("맑은 고딕", 12)).pack(pady=20)
            return

        for i, item in enumerate(self.todos):
            # 상위 항목 카드
            card = ctk.CTkFrame(self.list_frame, fg_color=C["input"], corner_radius=10,
                                border_width=1, border_color=C["border"])
            card.pack(fill="x", pady=(0,6))
            card.columnconfigure(1, weight=1)

            # 상위 행
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=10, pady=6)
            top_row.columnconfigure(1, weight=1)

            if self.editing_index == i:
                # 수정 모드
                edit_date_var = tk.StringVar(value=item.get("date", "날짜"))
                e_date_btn = ctk.CTkButton(top_row, textvariable=edit_date_var, fg_color=C["bg"], text_color=C["text"],
                                           width=80, height=24, font=("맑은 고딕", 11), corner_radius=6, hover_color=C["border"],
                                           command=lambda v=edit_date_var: self._open_calendar(v))
                e_date_btn.grid(row=0, column=0, padx=(0,4))

                edit_text_var = tk.StringVar(value=item["text"])
                e_text = ctk.CTkEntry(top_row, textvariable=edit_text_var, fg_color=C["bg"], text_color=C["text"],
                                      border_width=0, font=("맑은 고딕", 12), corner_radius=6)
                e_text.grid(row=0, column=1, sticky="ew", padx=4)
                e_text.focus_set()

                ctk.CTkButton(top_row, text="저장", fg_color=C["blue"], text_color="white", font=("맑은 고딕", 11),
                              width=40, height=24, corner_radius=6,
                              command=lambda x=i, t=edit_text_var, d=edit_date_var: self._save_edit(x, t, d)).grid(row=0, column=2, padx=2)
                ctk.CTkButton(top_row, text="취소", fg_color=C["input"], text_color=C["muted"], font=("맑은 고딕", 11),
                              width=40, height=24, corner_radius=6, hover_color=C["border"],
                              command=self._cancel_edit).grid(row=0, column=3)
                
                e_text.bind("<Return>", lambda e, x=i, t=edit_text_var, d=edit_date_var: self._save_edit(x, t, d))
            else:
                # 보기 모드
                ctk.CTkLabel(top_row, text=f"{i+1}", text_color=C["blue"],
                             font=("맑은 고딕", 12, "bold"), width=20).grid(row=0, column=0)
                ctk.CTkLabel(top_row, text=item["text"], text_color=C["text"],
                             font=("맑은 고딕", 13), anchor="w").grid(row=0, column=1, sticky="ew", padx=6)

                if item.get("date"):
                    d_text = item["date"]
                    # UI: 연도 2자리 (YY.MM.DD)
                    if "~" in d_text:
                        parts = d_text.split("~")
                        new_parts = []
                        for p in parts:
                            p = p.strip()
                            if len(p) >= 10 and p[4] == '-':
                                new_parts.append(p[2:].replace("-", "."))
                            else:
                                new_parts.append(p)
                        d_text = "~".join(new_parts)
                    elif len(d_text) >= 10 and d_text[4] == '-':
                        d_text = d_text[2:].replace("-", ".")

                    ctk.CTkLabel(top_row, text=d_text, text_color=C["muted"],
                                 font=("맑은 고딕", 11)).grid(row=0, column=2, padx=4)

                pin_txt = "📌" if item.get("pinned") else "📍"
                pin_col = C["blue"] if item.get("pinned") else "transparent"
                ctk.CTkButton(top_row, text=pin_txt, fg_color=pin_col, text_color=C["text"],
                              font=("맑은 고딕", 12), width=30, height=24, corner_radius=6, hover_color=C["border"],
                              command=lambda x=i: self._toggle_pin(x)).grid(row=0, column=3, padx=2)

                ctk.CTkButton(top_row, text="✎", fg_color="transparent", text_color=C["muted"],
                              font=("맑은 고딕", 12), width=30, height=24, corner_radius=6, hover_color=C["border"],
                              command=lambda x=i: self._start_edit(x)).grid(row=0, column=4, padx=2)

                sub_count = len(item["sub"])
                sub_label = f"▲ {sub_count}" if item["open"] else f"▼ {sub_count if sub_count else '+'}"
                ctk.CTkButton(top_row, text=sub_label, fg_color="transparent", text_color=C["muted"],
                              font=("맑은 고딕", 11), width=40, height=24, corner_radius=6, hover_color=C["border"],
                              command=lambda x=i: self._toggle_sub(x)).grid(row=0, column=5, padx=4)
                ctk.CTkButton(top_row, text="✕", fg_color="transparent", text_color=C["muted"],
                              font=("맑은 고딕", 12), width=30, height=24, corner_radius=6, hover_color=C["border"],
                              command=lambda x=i: self._remove_item(x)).grid(row=0, column=6)

            # 하위 영역
            if item["open"]:
                sub_frame = ctk.CTkFrame(card, fg_color="#0a1628", corner_radius=8,
                                         border_width=0)
                sub_frame.pack(fill="x", padx=10, pady=(0,10))

                for j, sub in enumerate(item["sub"]):
                    sr = ctk.CTkFrame(sub_frame, fg_color="transparent")
                    sr.pack(fill="x", padx=14, pady=2)
                    sr.columnconfigure(1, weight=1)
                    ctk.CTkLabel(sr, text="◦", text_color=C["blue"],
                                 font=("맑은 고딕", 12)).grid(row=0, column=0)
                    ctk.CTkLabel(sr, text=sub, text_color=C["muted"],
                                 font=("맑은 고딕", 12), anchor="w").grid(
                        row=0, column=1, sticky="ew", padx=6)
                    ctk.CTkButton(sr, text="✕", fg_color="transparent", text_color=C["muted"],
                                  font=("맑은 고딕", 10), width=24, height=20, corner_radius=4, hover_color=C["border"],
                                  command=lambda x=i,y=j: self._remove_sub(x,y)).grid(row=0, column=2)

                # 하위 입력
                sub_add = ctk.CTkFrame(sub_frame, fg_color="transparent")
                sub_add.pack(fill="x", padx=14, pady=(4,8))
                sub_add.columnconfigure(0, weight=1)
                sub_var = tk.StringVar()
                sub_entry = ctk.CTkEntry(sub_add, textvariable=sub_var,
                                         fg_color=C["input"], text_color=C["text"],
                                         border_width=0, font=("맑은 고딕", 11), height=28, corner_radius=6)
                sub_entry.grid(row=0, column=0, sticky="ew", ipady=3)
                sub_entry.insert(0, "하위 항목 입력 후 Enter...")
                sub_entry.configure(text_color=C["muted"])
                sub_entry.bind("<FocusIn>",  lambda e, v=sub_var, en=sub_entry: (
                    en.delete(0,"end"), en.configure(text_color=C["text"])) if v.get().startswith("하위") else None)
                sub_entry.bind("<Return>", lambda e, x=i, v=sub_var: self._add_sub(x, v))
                ctk.CTkButton(sub_add, text="추가", fg_color=C["green"], text_color="white",
                              font=("맑은 고딕", 11), width=40, height=28, corner_radius=6,
                              command=lambda x=i, v=sub_var: self._add_sub(x, v)).grid(
                    row=0, column=1, padx=(6,0))

    def _start_edit(self, index):
        self.editing_index = index
        self._render_list()

    def _save_edit(self, index, text_var, date_var):
        if text_var.get().strip():
            self.todos[index]["text"] = text_var.get().strip()
            d = date_var.get()
            self.todos[index]["date"] = "" if d == "날짜" else d
        self.editing_index = None
        self._render_list()
        self._refresh_preview_delayed()

    def _cancel_edit(self):
        self.editing_index = None
        self._render_list()

    # ── 전송 ──────────────────────────────────────────────
    def _send(self):
        ip = self.ip_var.get().strip()
        if not ip:
            self._set_status("X4 IP 주소를 먼저 입력해주세요!", error=True)
            return
        if not self.todos:
            self._set_status("할 일을 먼저 추가해주세요!", error=True)
            return

        self.btn_send.configure(state="disabled", text="⏳  전송 중...")
        self._set_status("BMP 생성 중...", error=False)

        def run():
            ok, msg = send_to_x4(ip, self.todos, self.font_scale, self.title_text)
            self.after(0, lambda: self._after_send(ok, msg))
        threading.Thread(target=run, daemon=True).start()

    def _after_send(self, ok, msg):
        self._set_status(msg, error=not ok)
        self.btn_send.configure(state="normal", text="📲  X4로 전송하기")
        if ok:
            self._refresh_preview_now()

    def _set_status(self, msg, error=False):
        self.status_lbl.configure(text=msg,
                                  text_color=self.C["err"] if error else self.C["ok"])

    # ── 미리보기 ──────────────────────────────────────────
    def _refresh_preview_delayed(self):
        if self.preview_after:
            self.after_cancel(self.preview_after)
        self.preview_after = self.after(500, self._refresh_preview_now)

    def _refresh_preview_now(self):
        def run():
            try:
                if self.todos:
                    # 임시 BMP 경로 (저장 안 함)
                    tmp_path = os.path.join(APP_DIR, "_preview_tmp.bmp")
                    orig = BMP_FILENAME

                    # create_bmp를 tmp 경로로 유도하기 위해 전역 임시 교체
                    import builtins
                    todos_copy = [dict(t) for t in self.todos]
                    img = create_bmp(todos_copy, self.font_scale, self.title_text)
                else:
                    img = Image.new("RGB", (IMG_W, IMG_H), "white")
                    draw = ImageDraw.Draw(img)
                    fp = resolve_font()
                    fnt = get_font(fp, 20) if fp else ImageFont.load_default()
                    msg = "할 일을 추가해보세요!"
                    try:
                        bb = draw.textbbox((0,0), msg, font=fnt)
                        tw = bb[2]-bb[0]
                    except:
                        tw = 160
                    draw.text(((IMG_W-tw)//2, IMG_H//2), msg, fill="#aaaaaa", font=fnt)

                # 패널 너비에 맞게 리사이즈
                pw = 236 # 고정 너비 (패널 260 - 패딩 24)
                ph = int(pw * IMG_H / IMG_W)
                photo = ctk.CTkImage(light_image=img, dark_image=img, size=(pw, ph))
                self.after(0, lambda: self._set_preview(photo))
            except Exception as e:
                pass
        threading.Thread(target=run, daemon=True).start()

    def _set_preview(self, photo):
        self.preview_lbl.configure(image=photo)
        self.preview_lbl._photo = photo  # GC 방지

# ── 실행 ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
