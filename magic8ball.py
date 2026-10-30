"""Run with `python magic8ball.py`; uses Python's built-in Tkinter GUI."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from PIL import Image, ImageTk

from answers import ask_ball, normalize_inputs, question_hint


BG = "#10091b"
PANEL = "#211331"
INPUT_BG = "#140b22"
TEXT = "#f4eaff"
MUTED = "#bea9d2"
ACCENT = "#E653E6"
EDGE = "#7544a5"
SPARKLE_COLORS = (ACCENT, "#E653E6", "#fff0a6")
ANSWER_COLORS = {
    "yes": ("#214936", "#8af0b2"),
    "maybe": ("#5a3f24", "#ffdc85"),
    "no": ("#592638", "#E653E6"),
}
IDLE_ANSWER = "Ask a yes-or-no question."
ASSET_DIR = Path(__file__).resolve().parent / "magic_8_ball_individual_ui_assets"


def answer_artwork(reading):
    """Choose an illustration without replacing the exact traditional answer."""
    if reading.answer_type != "maybe":
        return f"answer_{reading.answer_type}"
    if "predict" in reading.answer.lower():
        return "answer_cannot_predict"
    if "again" in reading.answer.lower():
        return "answer_ask_again"
    return "answer_maybe"


def blend_color(start, end, progress):
    channels = [round(int(start[i:i + 2], 16) * (1 - progress) + int(end[i:i + 2], 16) * progress)
                for i in (1, 3, 5)]
    return "#" + "".join(f"{channel:02x}" for channel in channels)


def pixelate_artwork(picture, size, pixel_scale=1):
    picture.thumbnail((max(1, size[0] // pixel_scale),
                       max(1, size[1] // pixel_scale)),
                      Image.Resampling.LANCZOS)
    picture = picture.resize((picture.width * pixel_scale,
                              picture.height * pixel_scale),
                             Image.Resampling.NEAREST)
    picture.thumbnail(size, Image.Resampling.NEAREST)
    return picture


class Magic8Ball(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Magic 8-Ball // Pixel Oracle")
        self.geometry("980x820")
        self.minsize(900, 760)
        self.configure(bg=BG)
        self.name = tk.StringVar()
        self.status = tk.StringVar()
        self.greeting = tk.StringVar(value="A little mystery awaits.")
        self.last_question = tk.StringVar(value="Your answer will appear below the ball.")
        self.busy = False
        self._after_id = None
        self._shake_offset = 0
        self._pending_question = None
        self.sparkles = []
        self.readings = []
        self._style()
        self._load_artwork()
        self._build()
        self.bind("<Control-Return>", self.on_enter)
        self.name_entry.bind("<Return>", self.on_enter)
        self.question_entry.bind("<Return>", self.on_enter)
        self.question_entry.bind("<KP_Enter>", self.on_enter)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.question_entry.focus_set()

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TScrollbar", background=EDGE, troughcolor=INPUT_BG,
                        arrowcolor=ACCENT, bordercolor=BG, relief="flat")
        style.map("TScrollbar", background=[("active", ACCENT)])

    def _load_artwork(self):
        sizes = {
            "ball_idle": (370, 320), "ball_shaking": (370, 320), "ball_answer_yes": (370, 320),
            "prompt_triangle": (92, 82), "question_icon": (30, 28),
        }
        for name in ("yes", "no", "maybe", "ask_again", "cannot_predict"):
            sizes[f"answer_{name}"] = (82, 82)
            sizes[f"overlay_{name}"] = (172, 172)
        self.artwork = {}
        for name, size in sizes.items():
            filename = name.replace("overlay_", "answer_")
            with Image.open(ASSET_DIR / f"{filename}.png") as original:
                pixel_scale = 2 if name in ("answer_ask_again", "overlay_ask_again") else (
                    3 if name.startswith(("ball_", "answer_", "overlay_")) else 1)
                picture = pixelate_artwork(original.convert("RGBA"), size, pixel_scale)
                self.artwork[name] = ImageTk.PhotoImage(picture, master=self)

    def label(self, parent, text=None, variable=None, size=11, color=TEXT, **kwargs):
        return tk.Label(parent, text=text, textvariable=variable, bg=parent["bg"],
                        fg=color, font=("Consolas", size, "bold" if size >= 16 else "normal"),
                        **kwargs)

    def _build(self):
        page = tk.Frame(self, bg=BG, padx=28, pady=14)
        page.pack(fill="both", expand=True)
        self.label(page, "[ COSMIC ARCADE ]", size=10, color=ACCENT).pack(anchor="w")
        self.label(page, "MAGIC 8-BALL", size=26).pack(anchor="w", pady=(3, 0))
        self.label(page, "Ask the cosmos. Let the pixels decide.", color=MUTED).pack(anchor="w")

        content = tk.Frame(page, bg=BG)
        content.pack(fill="both", expand=True, pady=(10, 8))
        content.columnconfigure(0, weight=1, uniform="half")
        content.columnconfigure(1, weight=1, uniform="half")
        content.rowconfigure(0, weight=1)

        form_border = tk.Frame(content, bg=EDGE, padx=3, pady=3)
        form_border.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        form = tk.Frame(form_border, bg=PANEL, padx=19, pady=16)
        form.pack(fill="both", expand=True)
        self.form = form
        self.label(form, "PLAYER ONE", size=10, color=ACCENT).pack(anchor="w")
        self.question_decor = self.label(
            form, "☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆",
            size=12, color=ACCENT, justify="center")
        self.question_decor.pack(fill="x", pady=(8, 12))
        self.label(form, "Your name (optional)").pack(anchor="w", pady=(0, 6))
        self.name_entry = tk.Entry(form, textvariable=self.name, font=("Consolas", 12),
                                   bg=INPUT_BG, fg=TEXT, insertbackground=ACCENT, relief="flat",
                                   highlightthickness=2, highlightbackground=EDGE,
                                   highlightcolor=ACCENT)
        self.name_entry.pack(fill="x", ipady=9)
        question_heading = tk.Frame(form, bg=PANEL)
        question_heading.pack(fill="x", pady=(10, 4))
        self.label(question_heading, image=self.artwork["question_icon"]).pack(side="left", padx=(0, 7))
        self.question_label = self.label(question_heading, "Enter a yes or no question")
        self.question_label.pack(side="left")
        self.question_entry = tk.Text(form, height=3, width=25, font=("Consolas", 12), wrap="word",
                                      bg=INPUT_BG, fg=TEXT, insertbackground=ACCENT, relief="flat",
                                      highlightthickness=2, highlightbackground=EDGE,
                                      highlightcolor=ACCENT, padx=10, pady=10)
        self.question_entry.pack(fill="x")
        self.question_hint_label = self.label(
            form, "EXAMPLE: Will I finish my project today?", size=9, color=MUTED,
            wraplength=310, justify="left")
        self.question_hint_label.pack(anchor="w", pady=(6, 16))
        self.ask_button = self.pixel_button(form, "ASK THE 8-BALL", self.reveal, primary=True)
        self.ask_button.pack(fill="x")
        self.status_label = self.label(form, variable=self.status, color=MUTED, size=10,
                                      wraplength=310, justify="left", anchor="w")
        self.status_label.pack(fill="x", pady=(10, 0))
        self.label(form, "RECENT READINGS / LAST 5", size=9, color=ACCENT).pack(anchor="w", pady=(14, 6))
        history_frame = tk.Frame(form, bg=INPUT_BG, highlightthickness=2,
                                 highlightbackground=EDGE)
        history_frame.pack(fill="both", expand=True)
        self.history = tk.Text(history_frame, height=3, width=25, font=("Consolas", 9), wrap="word",
                               bg=INPUT_BG, fg=MUTED, relief="flat", padx=8, pady=6, state="disabled")
        scroll = ttk.Scrollbar(history_frame, command=self.history.yview)
        self.history.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.history.pack(fill="both", expand=True)
        for kind, (_, color) in ANSWER_COLORS.items():
            self.history.tag_configure(kind, foreground=color)
        self._update_history()

        result_border = tk.Frame(content, bg=EDGE, padx=3, pady=3)
        result_border.grid(row=0, column=1, sticky="nsew")
        result = tk.Frame(result_border, bg=BG)
        result.pack(fill="both", expand=True)
        self.greeting_label = self.label(result, variable=self.greeting, size=16, color=ACCENT,
                                         wraplength=370)
        self.greeting_label.pack(pady=(8, 6))
        self.ball = tk.Canvas(result, width=380, height=424, bg=BG, highlightthickness=0)
        self.ball.pack()
        self._draw_ball()
        self.last_question_label = self.label(result, variable=self.last_question, color=MUTED, size=10,
                                               wraplength=360, justify="center")
        self.last_question_label.pack(padx=8, pady=(0, 10))
        self.clear_button = self.pixel_button(result, "CLEAR / NEW QUESTION", self.clear)
        self.clear_button.pack()
        self.label(result, "GREEN: YES   GOLD: MAYBE   PINK: NO", size=8, color=MUTED).pack(pady=12)
        self.label(page, "PIXEL ORACLE // PYTHON DESKTOP EDITION", size=9, color=MUTED).pack(anchor="w")
        self.label(page, "FOR FUN / ENTER TO ASK / HISTORY CLEARS ON EXIT", size=8, color=MUTED).pack(anchor="w", pady=(4, 0))
        self.form.bind("<Configure>", self._resize_form_text)
        result.bind("<Configure>", self._resize_result_text)
        self._resize_form_text()
        self._resize_result_text()

    def _draw_ball(self):
        self.ball_art = self.ball.create_image(190, 160, image=self.artwork["ball_idle"], tags="sphere")
        self.answer_ring = self.ball.create_oval(102, 72, 278, 248, outline=ACCENT, width=3,
                                                 state="hidden", tags="sphere")
        self.medallion = self.ball.create_image(190, 160, image=self.artwork["overlay_yes"],
                                                state="hidden", tags="sphere")
        for index, (x, y) in enumerate(((34, 52), (346, 56), (32, 274), (348, 270))):
            blocks = []
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                blocks.append(self.ball.create_rectangle(
                    x + dx * 4 - 2, y + dy * 4 - 2, x + dx * 4 + 2, y + dy * 4 + 2,
                    fill=SPARKLE_COLORS[index % len(SPARKLE_COLORS)], outline="",
                    tags=("sphere", "sparkle")))
            self.sparkles.append(blocks)
        self.answer_frame = self.ball.create_rectangle(8, 330, 372, 420, fill=PANEL, outline=EDGE, width=2)
        self.answer_badge = self.ball.create_image(60, 375, image=self.artwork["prompt_triangle"])
        self.answer_item = self.ball.create_text(238, 375, text=IDLE_ANSWER, width=235,
                                                 justify="center", fill=TEXT,
                                                 font=("Consolas", 12, "bold"))

    def pixel_button(self, parent, text, command, primary=False):
        resting = ACCENT if primary else EDGE
        hover = "#f2c3ff" if primary else ACCENT
        button_bg = "#4b2470" if primary else PANEL
        button = tk.Button(parent, text=text, command=command,
                           font=("Consolas", 11 if primary else 9, "bold"),
                           bg=button_bg, fg=TEXT, activebackground="#64358e",
                           activeforeground=TEXT, relief="flat", bd=0, padx=10, pady=10,
                           cursor="hand2", highlightthickness=3, highlightbackground=resting,
                           highlightcolor=hover, takefocus=True)
        button.bind("<Enter>", lambda event: button.configure(highlightbackground=hover))
        button.bind("<Leave>", lambda event: button.configure(highlightbackground=resting))
        button.bind("<Return>", lambda event: (button.invoke(), "break")[-1])
        return button

    def _resize_form_text(self, event=None):
        wraplength = max(200, self.form.winfo_width() - 48)
        self.question_hint_label.configure(wraplength=wraplength)
        self.status_label.configure(wraplength=wraplength)

    def _resize_result_text(self, event=None):
        wraplength = max(220, self.ball.winfo_width() - 24)
        self.greeting_label.configure(wraplength=wraplength)
        self.last_question_label.configure(wraplength=wraplength)

    def _set_sparkle_phase(self, frame):
        for index, blocks in enumerate(self.sparkles):
            color = SPARKLE_COLORS[(frame // 2 + index) % len(SPARKLE_COLORS)]
            for block in blocks:
                self.ball.itemconfigure(block, fill=color)

    def on_enter(self, event=None):
        self.reveal()
        return "break"

    def reveal(self):
        if self.busy:
            return
        try:
            name, question = normalize_inputs(self.name.get(), self.question_entry.get("1.0", "end"))
        except ValueError as error:
            self.status.set(str(error))
            self.status_label.configure(fg="#E653E6")
            return
        hint = question_hint(question)
        if hint and self._pending_question != question:
            self._pending_question = question
            self.status.set(hint)
            self.status_label.configure(fg="#ffd17c")
            return
        self._pending_question = None
        reading = ask_ball(name, question)
        self.busy = True
        self.ask_button.configure(state="disabled")
        self.status.set("Consulting the spirits…")
        self.status_label.configure(fg=MUTED)
        self.greeting.set("A little shake of fate…")
        self.ball.itemconfigure(self.answer_item, text="")
        self.ball.itemconfigure(self.ball_art, image=self.artwork["ball_shaking"])
        self.ball.itemconfigure(self.medallion, state="hidden")
        self.ball.itemconfigure(self.answer_ring, state="hidden")
        self.ball.itemconfigure(self.answer_badge, image=self.artwork["prompt_triangle"])
        self.ball.itemconfigure(self.answer_frame, outline=ACCENT)
        self._shake_tick(reading, 0)

    def _shake_tick(self, reading, frame):
        self._after_id = None
        self._set_sparkle_phase(frame)
        # Twenty frames at 25 ms give a half-second shake, returning to the center.
        if frame == 20:
            self.ball.move("sphere", -self._shake_offset, 0)
            self._shake_offset = 0
            self._set_sparkle_phase(0)
            self._start_fade(reading)
            return
        offset = (7 if frame % 2 == 0 else -7) * (1 - frame / 20)
        self.ball.move("sphere", offset - self._shake_offset, 0)
        self._shake_offset = offset
        self._after_id = self.after(25, self._shake_tick, reading, frame + 1)

    def _start_fade(self, reading):
        background, border = ANSWER_COLORS[reading.answer_type]
        art = answer_artwork(reading)
        ball = "ball_answer_yes" if reading.answer_type == "yes" else "ball_idle"
        self.ball.itemconfigure(self.ball_art, image=self.artwork[ball])
        # Only affirmative readings use the ball with "Yes" baked into its artwork.
        self.ball.itemconfigure(self.medallion, image=self.artwork[art.replace("answer_", "overlay_")],
                                state="hidden" if reading.answer_type == "yes" else "normal")
        self.ball.itemconfigure(self.answer_ring, outline=border,
                                state="hidden" if reading.answer_type == "yes" else "normal")
        self.ball.itemconfigure(self.answer_badge, image=self.artwork[art])
        self.ball.itemconfigure(self.answer_frame, outline=border)
        self.ball.itemconfigure(self.answer_item, text=reading.answer, fill=PANEL)
        self.greeting.set(f"{reading.name}, the spirits say…" if reading.name else "The spirits say…")
        self.last_question.set(f'“{reading.question}”')
        self._fade_tick(reading, 0)

    def _fade_tick(self, reading, frame):
        self._after_id = None
        background, border = ANSWER_COLORS[reading.answer_type]
        self.ball.itemconfigure(self.answer_item, fill=blend_color(PANEL, TEXT, frame / 12))
        if frame < 12:
            self._after_id = self.after(30, self._fade_tick, reading, frame + 1)
            return
        self.busy = False
        self.ask_button.configure(state="normal")
        self.status.set("Answer revealed. Ask again whenever you're ready.")
        self.status_label.configure(fg=border)
        self.readings.insert(0, reading)
        del self.readings[5:]
        self._update_history()

    def _update_history(self):
        self.history.configure(state="normal")
        self.history.delete("1.0", "end")
        if not self.readings:
            self.history.insert("end", "No questions yet.")
        for reading in self.readings:
            self.history.insert("end", f"{reading.question}\n")
            personal = f"{reading.name}, the spirits say… " if reading.name else ""
            self.history.insert("end", f"{personal}{reading.answer}\n\n", reading.answer_type)
        self.history.configure(state="disabled")

    def _cancel_animation(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.ball.move("sphere", -self._shake_offset, 0)
        self._shake_offset = 0
        self._set_sparkle_phase(0)
        self.busy = False
        self.ask_button.configure(state="normal")

    def clear(self):
        self._cancel_animation()
        self._pending_question = None
        self.question_entry.delete("1.0", "end")
        self.ball.itemconfigure(self.answer_item, text=IDLE_ANSWER, fill=TEXT)
        self.ball.itemconfigure(self.ball_art, image=self.artwork["ball_idle"])
        self.ball.itemconfigure(self.medallion, state="hidden")
        self.ball.itemconfigure(self.answer_ring, state="hidden")
        self.ball.itemconfigure(self.answer_badge, image=self.artwork["prompt_triangle"])
        self.ball.itemconfigure(self.answer_frame, outline=EDGE)
        self.greeting.set("A little mystery awaits.")
        self.last_question.set("Your answer will appear below the ball.")
        self.status.set("Cleared. Your recent answers are kept below.")
        self.status_label.configure(fg=MUTED)
        self.question_entry.focus_set()

    def destroy(self):
        self._cancel_animation()
        super().destroy()


if __name__ == "__main__":
    Magic8Ball().mainloop()
