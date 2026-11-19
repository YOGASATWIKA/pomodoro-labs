from datetime import datetime

from pomodoro_labs.config import DEFAULTS
from pomodoro_labs.timing import (advance, auto_state, fmt, parse_duration,
                                  parse_pomodoro, valid_time)

SCHED = DEFAULTS["schedule"]
POMO = DEFAULTS["pomodoro"]
DUR = {"work": 25 * 60, "short": 5 * 60, "long": 10 * 60}


def test_parse_duration():
    assert parse_duration("25") == 1500
    assert parse_duration("1:30") == 90
    assert parse_duration("1:00:00") == 3600


def test_parse_pomodoro_defaults_and_errors():
    assert parse_pomodoro("30/10/20", POMO) == {"work": 1800, "short": 600, "long": 1200}
    assert parse_pomodoro("30", POMO)["short"] == 300
    try:
        parse_pomodoro("0/5/10", POMO)
    except ValueError:
        pass
    else:
        raise AssertionError("harus ValueError")


def test_advance_cycle():
    assert advance("work", 1, 4) == ("short", 1)
    assert advance("short", 1, 4) == ("work", 2)
    assert advance("work", 4, 4) == ("long", 4)
    assert advance("long", 4, 4) == ("work", 1)


def test_fmt_and_valid_time():
    assert fmt(65) == "01:05"
    assert fmt(3725) == "1:02:05"
    assert fmt(-3) == "00:00"
    assert valid_time("9:05") == "09:05"
    assert valid_time("25:00") is None


def test_auto_state_work_and_break():
    mon = datetime(2026, 11, 16)  # Senin
    st = auto_state(mon.replace(hour=9, minute=10), DUR, SCHED, 4)
    assert st[1:3] == ("work", 1)
    assert st[3] == mon.replace(hour=9, minute=25)
    st = auto_state(mon.replace(hour=9, minute=27), DUR, SCHED, 4)
    assert st[1] == "short"


def test_auto_state_lunch_and_off():
    mon = datetime(2026, 11, 16)
    assert auto_state(mon.replace(hour=13, minute=0), DUR, SCHED, 4)[1] == "lunch"
    st = auto_state(mon.replace(hour=19), DUR, SCHED, 4)
    assert st[1] == "off" and st[3] == datetime(2026, 11, 17, 9, 0)


def test_auto_state_weekend_goes_to_monday():
    sat = datetime(2026, 11, 21, 10)
    st = auto_state(sat, DUR, SCHED, 4)
    assert st[1] == "off" and st[3] == datetime(2026, 11, 23, 9, 0)
