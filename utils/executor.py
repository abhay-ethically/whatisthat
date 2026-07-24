"""Safe command execution helpers."""
import re
import shutil
import subprocess

from .formatter import danger, info, success, warning


# Patterns that are considered dangerous and blocked by default.
DANGEROUS_PATTERNS = [
    r"rm\s+-[rf]*[rf]\s+/",
    r"mkfs\.\w+",
    r"dd\s+if=/dev/\w+\s+of=/dev/[sh]d[a-z]",
    r">\s*/dev/[sh]d[a-z]",
    r":\(\)\{ \|:\| & \};:",  # fork bomb
    r"chmod\s+-R\s+777\s+/",
    r"chown\s+-R\s+\w+:\w+\s+/",
    r"rm\s+-[rf]*[rf]\s+--no-preserve-root",
    r"\|.*sh",
    r"curl.*\|.*bash",
    r"wget.*\|.*sh",
]

DANGEROUS_REGEX = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS]


def is_dangerous(command_str):
    """Check if a command string matches a dangerous pattern."""
    for pattern in DANGEROUS_REGEX:
        if pattern.search(command_str):
            return True
    return False


def tool_installed(tool_name):
    """Return True if the binary for tool_name is available on PATH."""
    return shutil.which(tool_name) is not None


def preview_command(command_str):
    """Print a command preview before execution."""
    info("About to execute:")
    print(f"   $ {command_str}")


def execute_command(command_str, timeout=60):
    """Execute a command safely after checks.

    Returns a dict with keys: success (bool), returncode, stdout, stderr.
    """
    command_str = command_str.strip()
    if not command_str:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "Empty command"}

    if is_dangerous(command_str):
        print(danger("This command matches a dangerous pattern and is blocked."))
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "Blocked by safety filter"}

    tool = command_str.split()[0]
    if not tool_installed(tool):
        print(warning(f"'{tool}' was not found on PATH. It may not be installed."))
        print(info("You can usually install it with: sudo apt install " + tool))
        # Still ask for confirmation; don't block outright because the tool might be elsewhere.

    preview_command(command_str)
    try:
        result = subprocess.run(
            command_str,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        print(danger(f"Command timed out after {timeout} seconds."))
        return {"success": False, "returncode": -1, "stdout": "", "stderr": "Timed out"}
    except FileNotFoundError:
        print(danger(f"Command not found: {tool}"))
        return {"success": False, "returncode": -1, "stdout": "", "stderr": f"{tool}: command not found"}
    except Exception as exc:
        print(danger(f"Execution failed: {exc}"))
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(exc)}


def ask_and_run(command_str):
    """Ask the user for confirmation and run the command if approved."""
    if is_dangerous(command_str):
        print(danger("This command is blocked for safety."))
        return None

    preview_command(command_str)
    print(warning("Do you want to run this command? Type 'yes' to confirm, anything else to cancel."))
    answer = input("Confirm: ").strip().lower()
    if answer != "yes":
        info("Execution cancelled.")
        return None

    result = execute_command(command_str)
    if result["success"]:
        print(success(f"Exited with code {result['returncode']}"))
    else:
        print(danger(f"Exited with code {result['returncode']}"))
    if result["stdout"]:
        print("--- stdout ---")
        print(result["stdout"])
    if result["stderr"]:
        print("--- stderr ---")
        print(result["stderr"])
    return result
