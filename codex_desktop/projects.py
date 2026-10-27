import json
import os
import shutil
import subprocess
from pathlib import Path

MAX_SUBJECTS = 5


class GitError(Exception):
	pass


class Projects:
	def __init__(self):
		self.path = Path(os.environ.get("APPDATA", str(Path.home()))) / "CodexDesktop" / "projects.json"

	def load(self):
		try:
			data = json.loads(self.path.read_text(encoding="utf-8"))
		except (OSError, ValueError):
			data = {}
		folders = data.get("folders") if isinstance(data, dict) else None
		return {
			"automatic": bool(data.get("automatic", True)) if isinstance(data, dict) else True,
			"folders": [folder for folder in folders if isinstance(folder, str)] if isinstance(folders, list) else [],
		}

	def save(self, settings):
		self.path.parent.mkdir(parents=True, exist_ok=True)
		temporary = self.path.with_suffix(".new")
		temporary.write_text(json.dumps(settings, indent="\t"), encoding="utf-8")
		os.replace(temporary, self.path)


def run_git(folder, *arguments):
	environment = dict(os.environ, GIT_TERMINAL_PROMPT="0")
	try:
		result = subprocess.run(
			["git", "-C", folder, *arguments],
			capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
			stdin=subprocess.DEVNULL, env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
		)
	except subprocess.TimeoutExpired as error:
		raise GitError("Git did not finish within 2 minutes.") from error
	except OSError as error:
		raise GitError(f"Git could not be started: {error}") from error
	if result.returncode != 0:
		lines = [line.strip() for line in (result.stderr or result.stdout).splitlines() if line.strip()]
		raise GitError(lines[-1] if lines else f"Git stopped with code {result.returncode}.")
	return result.stdout.strip()


def is_repository(folder):
	return (Path(folder) / ".git").exists()


def update(folder):
	name = Path(folder).name
	if not Path(folder).is_dir():
		return f"{name} was not updated, because the folder {folder} no longer exists.", True
	if not is_repository(folder):
		return f"{name} was not updated, because it is not a Git repository.", True
	try:
		before = run_git(folder, "rev-parse", "HEAD")
		run_git(folder, "pull", "--ff-only")
		after = run_git(folder, "rev-parse", "HEAD")
		if before == after:
			return f"{name} is already up to date.", False
		count = int(run_git(folder, "rev-list", "--count", f"{before}..{after}"))
		files = run_git(folder, "diff", "--shortstat", before, after)
		subjects = run_git(folder, "log", "--format=%s", f"-{MAX_SUBJECTS}", f"{before}..{after}").splitlines()
	except GitError as error:
		if "fast-forward" in str(error):
			return f"{name} was not updated, because this computer has its own changes that are not on GitHub, so Git cannot add the new changes safely. Send your changes to GitHub first, or ask me for help.", True
		return f"{name} was not updated. Git said: {error}", True
	changes = "1 new change" if count == 1 else f"{count} new changes"
	text = f"{name} got {changes}, {files.strip() or 'with no file differences'}."
	if subjects:
		more = f", and {count - len(subjects)} more" if count > len(subjects) else ""
		text += " Changes: " + "; ".join(subjects) + more + "."
	return text, True


def update_all(folders):
	if shutil.which("git") is None:
		return "Git is not installed on this computer, so the local projects could not be updated. Install Git for Windows, then try again.", True
	results = [update(folder) for folder in folders]
	return " ".join(text for text, _ in results), any(important for _, important in results)
