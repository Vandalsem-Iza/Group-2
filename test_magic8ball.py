from time import monotonic, sleep
from unittest.mock import patch
import pytest
from PIL import Image

from answers import ANSWERS, Reading, ask_ball, question_hint
from magic8ball import (ANSWER_COLORS, ASSET_DIR, IDLE_ANSWER, Magic8Ball,
                        answer_artwork, pixelate_artwork)


@pytest.mark.parametrize('name,question,message', [
    ('Iza', '  ', 'type a question'),
    ('x' * 61, 'Will it rain?', '60'),
    ('Iza', 'x' * 301, '300'),
])
def test_invalid_inputs(name, question, message):
    with pytest.raises(ValueError, match=message):
        ask_ball(name, question)


@pytest.mark.parametrize('name', ['', '  ', 'Iza'])
def test_name_is_optional(name):
    reading = ask_ball(name, 'Will it rain?')
    assert reading.name == name.strip()
    assert reading.answer in ANSWERS


def test_notebook_pool_normalization_and_types():
    assert ANSWERS == (
        'without a doubt.', 'outlook good.', 'signs point to yes', 'it is certain.',
        'Definitely.', 'Concentrate and ask again.', 'My sources say no.',
        "Don't count on it.", 'Very doubtful.', 'absolutly not.', 'No.',
    )
    assert len(ANSWERS) == len(set(ANSWERS)) == 11
    types = []
    for answer in ANSWERS:
        with patch('answers.random.choice', return_value=answer) as choose:
            reading = ask_ball('  Iza  ', 'Will my\n project succeed?')
        choose.assert_called_once_with(ANSWERS)
        assert reading.name == 'Iza'
        assert reading.question == 'Will my project succeed?'
        assert reading.answer == answer
        types.append(reading.answer_type)
    assert types.count('yes') == 5
    assert types.count('maybe') == 1
    assert types.count('no') == 5
    assert Reading('', '', 'Definitely.').answer_type == 'yes'
    assert Reading('', '', 'Concentrate and ask again.').answer_type == 'maybe'
    assert Reading('', '', 'No.').answer_type == 'no'


@pytest.mark.parametrize('question', ['what should I do?', 'WHY is it raining?', 'How are you?', 'Will it rain'])
def test_question_nudges(question):
    assert question_hint(question)


def test_yes_no_question_has_no_nudge():
    assert question_hint('Will it rain?') == ''
    assert question_hint('Is this what I need?') == ''


@pytest.fixture(scope='module')
def application():
    window = Magic8Ball()
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def app(application):
    application.clear()
    application.name.set('')
    application.readings.clear()
    application._update_history()
    yield application
    application._cancel_animation()


def wait_for_reveal(app):
    deadline = monotonic() + 4
    while app.busy and monotonic() < deadline:
        app.update()
        sleep(0.005)
    assert not app.busy, 'Animation did not finish'


def set_question(app, question):
    app.question_entry.delete('1.0', 'end')
    app.question_entry.insert('1.0', question)


def test_updated_pixel_ui_copy_and_pink_color(app):
    assert app.status.get() != 'Ready when you are.'
    assert app.question_label.cget('text') == 'Enter a yes or no question'
    assert app.question_decor.cget('text') == '☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆ ☆'
    assert app.question_decor.cget('justify') == 'center'
    assert app.cget('bg') == '#10091b'
    assert app.artwork['ball_idle'].width() >= 340
    assert app.artwork['ball_idle'].width() < 370
    assert app.artwork['answer_yes'].width() >= 80
    assert ANSWER_COLORS['no'][1] == '#E653E6'


@pytest.mark.parametrize('art_name', ['answer_yes', 'answer_no', 'answer_ask_again'])
def test_answer_artwork_uses_consistent_pixelation(app, art_name):
    pixel_scale = 2 if art_name == 'answer_ask_again' else 3
    with Image.open(ASSET_DIR / f'{art_name}.png') as original:
        image = pixelate_artwork(original.convert('RGBA'), (82, 82), pixel_scale)
    for y in range(0, image.height - pixel_scale + 1, pixel_scale):
        for x in range(0, image.width - pixel_scale + 1, pixel_scale):
            color = image.getpixel((x, y))
            assert all(image.getpixel((x + dx, y + dy)) == color
                       for dx in range(pixel_scale) for dy in range(pixel_scale))


def test_button_validation_animation_and_clear(app):
    app.ask_button.invoke()
    assert 'type a question' in app.status.get()
    app.name.set('Iza')
    set_question(app, 'Will my project succeed?')
    original_position = app.ball.coords(app.ball_art)
    with patch('answers.random.choice', return_value='outlook good.') as choose:
        app.ask_button.invoke()
        assert app.busy
        assert app.ball.itemcget(app.answer_item, 'text') == ''
        app.reveal()  # Repeated clicks/Enter cannot queue duplicate readings.
        wait_for_reveal(app)
    choose.assert_called_once()
    assert app.ball.itemcget(app.answer_item, 'text') == 'outlook good.'
    assert 'Iza, the spirits say' in app.greeting.get()
    assert 'project succeed' in app.last_question.get()
    assert app.ball.coords(app.ball_art) == pytest.approx(original_position)
    assert app.ball.itemcget(app.answer_frame, 'outline') == ANSWER_COLORS['yes'][1]
    assert len(app.readings) == 1
    app.clear()
    assert not app.question_entry.get('1.0', 'end').strip()
    assert app.name.get() == 'Iza'
    assert app.ball.itemcget(app.answer_item, 'text') == IDLE_ANSWER
    assert len(app.readings) == 1
    assert 'outlook good.' in app.history.get('1.0', 'end')


def test_question_warning_can_be_overridden(app):
    set_question(app, 'What happens next?')
    with patch('answers.random.choice', return_value='Concentrate and ask again.') as choose:
        app.reveal()
        assert not app.busy
        assert 'yes-or-no' in app.status.get()
        choose.assert_not_called()
        app.reveal()
        wait_for_reveal(app)
    assert app.greeting.get() == 'The spirits say…'
    assert app.ball.itemcget(app.answer_frame, 'outline') == ANSWER_COLORS['maybe'][1]


def test_clear_cancels_an_inflight_reveal(app):
    set_question(app, 'Will it rain?')
    original_position = app.ball.coords(app.ball_art)
    app.reveal()
    assert app.busy
    assert app._after_id is not None
    app.clear()
    app.update()
    assert not app.busy
    assert app._after_id is None
    assert not app.readings
    assert app.ball.coords(app.ball_art) == pytest.approx(original_position)
    assert app.ball.itemcget(app.answer_item, 'text') == IDLE_ANSWER


def test_history_is_limited_and_red_answers_are_tinted(app):
    for index in range(6):
        set_question(app, f'Will attempt {index} work?')
        with patch('answers.random.choice', return_value='My sources say no.'):
            app.reveal()
        wait_for_reveal(app)
    assert len(app.readings) == 5
    history = app.history.get('1.0', 'end')
    assert 'attempt 0' not in history
    assert 'attempt 5' in history
    assert history.index('attempt 5') < history.index('attempt 1')
    assert app.ball.itemcget(app.answer_frame, 'outline') == ANSWER_COLORS['no'][1]


@pytest.mark.parametrize('answer', ANSWERS)
def test_artwork_matches_each_dynamic_answer(app, answer):
    reading = Reading('Iza', 'Will this work?', answer)
    app._start_fade(reading)
    art = answer_artwork(reading)
    assert app.ball.itemcget(app.answer_item, 'text') == answer
    assert app.ball.itemcget(app.answer_badge, 'image') == str(app.artwork[art])
    if reading.answer_type == 'yes':
        assert app.ball.itemcget(app.ball_art, 'image') == str(app.artwork['ball_answer_yes'])
        assert app.ball.itemcget(app.medallion, 'state') == 'hidden'
    else:
        assert app.ball.itemcget(app.ball_art, 'image') == str(app.artwork['ball_idle'])
        assert app.ball.itemcget(app.medallion, 'state') == 'normal'
    if answer == 'Concentrate and ask again.':
        assert art == 'answer_ask_again'


def test_idle_and_shaking_artwork(app):
    assert app.ball.itemcget(app.ball_art, 'image') == str(app.artwork['ball_idle'])
    assert app.ball.itemcget(app.answer_badge, 'image') == str(app.artwork['prompt_triangle'])
    set_question(app, 'Will this work?')
    app.reveal()
    assert app.ball.itemcget(app.ball_art, 'image') == str(app.artwork['ball_shaking'])
    app.clear()
    assert app.ball.itemcget(app.ball_art, 'image') == str(app.artwork['ball_idle'])
    assert app.ball.itemcget(app.answer_badge, 'image') == str(app.artwork['prompt_triangle'])
