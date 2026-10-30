# Magic 8-Ball

A Python desktop application for Iza Vandalsem's team, styled as a purple retro-pixel oracle with crisp answer lettering and bright pink accents (`#E653E6`). Enter a yes-or-no question and, optionally, your name, then click **Ask the 8-Ball** or press **Enter**. The lightly pixelated ball shakes with flickering sparkles for half a second, then a random answer from the supplied notebook fades into the answer card. Card borders show green for affirmative answers, gold for uncertain answers, or bright pink for negative answers. A supplied name personalizes the greeting and history.

Empty questions are blocked. Questions beginning with what/why/how or missing a final question mark get a gentle prompt; revise the question or click Ask again to proceed anyway. **Clear & ask something new** cancels any animation and clears the question and answer while keeping your name and the latest five readings. History is kept only until the app closes.

## Run the app

On 64-bit Windows, double-click `release/Magic8Ball.exe`. Python and extra files are not needed for the executable.

To run the source, install Python with Tkinter, install Pillow with `python -m pip install "Pillow>=11,<13"`, and run `python magic8ball.py` from this folder. Keep `magic_8_ball_individual_ui_assets/` beside the source. All entries stay in the current session; nothing is saved or sent anywhere.

## How the Python window works

1. **Create a window:** `Magic8Ball` extends `tk.Tk`. Its constructor sets the title, size, and background, then calls `_build()` to add the controls. `mainloop()` at the end keeps the window responsive.
2. **Add inputs:** `tk.Entry` is the one-line name box, connected to a `StringVar`. `tk.Text` is the multiline question box. `pack()` and `grid()` arrange controls inside separate frames.
3. **Connect a button:** `tk.Button(..., command=self.reveal)` runs `reveal()` when clicked. The button's `image` option displays the supplied button artwork. Use the method name without parentheses so it runs on a click rather than during startup.
4. **Read values:** `self.name.get()` reads the name. `self.question_entry.get("1.0", "end")` reads the question from the first character to the end.
5. **Choose an answer:** `answers.py` validates the entries and uses `random.choice(ANSWERS)` to select uniformly from the 11 responses in `magic8code.ipynb`: five affirmative, one uncertain, and five negative. `Reading.answer_type` supplies the color category. If adapting the answer list, update that classification too.
6. **Load and display artwork:** `_load_artwork()` uses Pillow to lightly pixelate and resize the ball and answer graphics consistently while preserving readable lettering and the original aspect ratios. It creates `ImageTk.PhotoImage` objects kept in `self.artwork`. `_draw_ball()` places the ball, block-built sparkles, smaller answer graphic, and dynamic text on a Canvas. The idle state uses `ball_idle.png` and `prompt_triangle.png`; shaking uses `ball_shaking.png`. Affirmative answers use `ball_answer_yes.png`. Other answers use the idle ball with a matching smaller medallion covering the number 8, so a negative or uncertain answer never displays the affirmative ball's baked-in Yes label. `answer_artwork()` selects Yes, No, Maybe, Ask again later, or Cannot predict now graphics, while the full answer stays dynamic. Pixel-style buttons and the question icon complete the purple arcade look.
7. **Animate without freezing:** `_shake_tick()` moves Canvas items tagged `sphere` every 25 milliseconds using `after()`, for 20 frames. `_fade_tick()` blends the answer text from the card background to white in 12 steps. The button is disabled during the animation, and repeated Enter presses are ignored. Clearing or closing cancels scheduled callbacks.
8. **Show and remember the response:** `self.ball.itemconfigure(self.answer_item, text=reading.answer)` updates the answer. `StringVar.set()` updates labels. The newest completed reading is inserted at the beginning of a list, limited to five, and rendered into a read-only history box.

The response list is copied verbatim from the supplied `magic8code.ipynb`, preserving its order, spelling, capitalization, and punctuation. The desktop interface, animation, input handling, and history are unchanged. A desktop Tkinter window runs locally; it is not displayed inside a hosted Colab notebook.

## Build and check

Run `python -m pip install -r requirements-build.txt`, then `./build.ps1` in PowerShell. The script runs pytest and creates `release/Magic8Ball.exe`. PyInstaller includes the Python runtime and Tkinter; `--onefile` creates a single executable and `--windowed` avoids a separate console window.

The build includes the entire artwork folder in the single executable, so you can run or share it without separate image files.

Run `python -m pytest -q` for checks of required questions, optional names, input limits, question nudges, the notebook response list and categories, repeated-click protection, actual animation completion, history retention, cancellation, idle/shaking states, and artwork mappings for all 11 responses.
