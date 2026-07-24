"""Terminal output formatting helpers."""
import os
import sys


def supports_color():
    """Return True if the terminal likely supports ANSI colors."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if sys.platform == "win32":
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    term = os.environ.get("TERM", "")
    return "dumb" not in term


USE_COLOR = supports_color()


_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def color(name, text):
    """Wrap text in the named color if supported."""
    if not USE_COLOR:
        return text
    return f"{_CODES.get(name, '')}{text}{_CODES['reset']}"


def header(text):
    return color("cyan", f"\n{'=' * 60}\n{text}\n{'=' * 60}")


def bot_name():
    return color("cyan", "LinuxBot")


def say_msg(text):
    return f"{bot_name()}: {text}"


def say(text):
    print(say_msg(text))


def command(text):
    return color("green", text)


def warning(text):
    return color("yellow", f"⚠️  {text}")


def danger(text):
    return color("red", f"🛑 {text}")


def info(text):
    return color("blue", f"ℹ️  {text}")


def success(text):
    return color("green", f"✅ {text}")
