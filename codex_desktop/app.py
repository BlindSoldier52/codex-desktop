import os
import socket
import threading
import time
import webbrowser
import winsound
from datetime import datetime
from pathlib import Path

import wx
import wx.adv

from .client import Client, ServerError, Unpaired
from .projects import Projects, is_repository, update_all
from .storage import Pairing

APP_NAME = "Codex Desktop"
DEFAULT_SERVER = "https://codex.gaming-space.site"
MAX_UPLOAD = 20 * 1024 ** 3
SKIPPED_FOLDERS = {"__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


def when(timestamp):
	return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S") if timestamp else ""


def size_text(number):
	value = float(number)
	for unit in ("B", "KB", "MB", "GB", "TB"):
		if value < 1024 or unit == "TB":
			return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
		value /= 1024


def gigabytes(number):
	return f"{number // 1024 ** 3} GB"


def labelled(parent, sizer, label, create, expand=True):
	text = wx.StaticText(parent, label=label)
	control = create()
	control.SetName(label.replace("&", ""))
	sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
	sizer.Add(control, 1 if expand else 0, wx.EXPAND | wx.ALL, 8)
	return control


class Worker:
	def __init__(self, window):
		self.window = window

	def run(self, job, done, failed=None):
		def target():
			try:
				result = job()
			except Unpaired as error:
				wx.CallAfter(self.window.handle_unpaired, error.message)
				return
			except ServerError as error:
				wx.CallAfter(failed or self.window.show_error, error.message)
				return
			except Exception as error:
				wx.CallAfter(failed or self.window.show_error, f"Something unexpected went wrong: {error}")
				return
			wx.CallAfter(done, result)

		threading.Thread(target=target, daemon=True).start()


class PairDialog(wx.Dialog):
	def __init__(self, parent):
		super().__init__(parent, title="Pair this computer with Codex", style=wx.DEFAULT_DIALOG_STYLE)
		self.result = None
		sizer = wx.BoxSizer(wx.VERTICAL)
		intro = wx.StaticText(self, label=(
			"This computer is not paired yet. On the Codex website, open the Devices page, "
			"select Create pairing code, then type the code here. You only need to do this once."
		))
		intro.Wrap(460)
		sizer.Add(intro, 0, wx.ALL, 8)
		self.server = labelled(self, sizer, "&Server address", lambda: wx.TextCtrl(self, value=DEFAULT_SERVER), False)
		self.code = labelled(self, sizer, "Pairing &code, 20 characters", lambda: wx.TextCtrl(self), False)
		self.name = labelled(self, sizer, "&Name for this computer", lambda: wx.TextCtrl(self, value=socket.gethostname()), False)
		self.message = wx.StaticText(self, label="")
		sizer.Add(self.message, 0, wx.ALL, 8)
		buttons = wx.StdDialogButtonSizer()
		self.pair_button = wx.Button(self, wx.ID_OK, "&Pair")
		self.pair_button.SetDefault()
		buttons.AddButton(self.pair_button)
		buttons.AddButton(wx.Button(self, wx.ID_CANCEL, "Cancel"))
		buttons.Realize()
		sizer.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 8)
		self.SetSizerAndFit(sizer)
		self.pair_button.Bind(wx.EVT_BUTTON, self.on_pair)
		self.code.SetFocus()

	def on_pair(self, event):
		server = self.server.GetValue().strip().rstrip("/")
		code = self.code.GetValue().strip()
		name = self.name.GetValue().strip() or socket.gethostname()
		if not code:
			self.warn("Type the pairing code first.")
			return
		self.pair_button.Disable()
		self.say("Pairing, please wait.")
		threading.Thread(target=self.pair, args=(server, code, name), daemon=True).start()

	def pair(self, server, code, name):
		try:
			client = Client(server)
			result = client.pair(code, name)
			Pairing().save(client.server, result["token"], result["name"])
		except ServerError as error:
			wx.CallAfter(self.fail, error.message)
			return
		except OSError as error:
			wx.CallAfter(self.fail, f"The pairing could not be saved on this computer: {error}")
			return
		wx.CallAfter(self.finish, client)

	def finish(self, client):
		self.result = client
		self.EndModal(wx.ID_OK)

	def fail(self, message):
		self.pair_button.Enable()
		self.warn(message)

	def say(self, text):
		self.message.SetLabel(text)
		self.message.Wrap(460)
		self.Layout()
		self.Fit()

	def warn(self, text):
		self.say(text)
		wx.MessageBox(text, APP_NAME, wx.OK | wx.ICON_INFORMATION, self)
		self.code.SetFocus()


class TaskDialog(wx.Dialog):
	def __init__(self, parent, task):
		super().__init__(parent, title=f"Task {task['id']}", size=(760, 640), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		sizer = wx.BoxSizer(wx.VERTICAL)
		lines = [f"Task {task['id']} is {task['status_text']}.", f"Submitted at {when(task['created'])}."]
		if task.get("finished"):
			lines.append(f"Finished at {when(task['finished'])}.")
		self.summary = labelled(self, sizer, "&Status", lambda: wx.TextCtrl(self, value=" ".join(lines), style=wx.TE_READONLY), False)
		self.request = labelled(self, sizer, "&Request", lambda: wx.TextCtrl(self, value=task["prompt"], style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2, size=(-1, 110)), False)
		self.answer = labelled(self, sizer, "Codex &answer", lambda: wx.TextCtrl(self, value=task["output"] or "", style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2))
		close = wx.Button(self, wx.ID_CANCEL, "&Close")
		sizer.Add(close, 0, wx.ALL | wx.ALIGN_RIGHT, 8)
		self.SetSizer(sizer)
		self.SetEscapeId(wx.ID_CANCEL)
		self.answer.SetFocus()


class TasksPage(wx.Panel):
	def __init__(self, parent, window):
		super().__init__(parent)
		self.window = window
		self.task_id = None
		self.received = 0
		self.stop_stream = False
		self.history = []
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.prompt = labelled(self, sizer, "&Task for Codex", lambda: wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 120)), False)
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.submit = wx.Button(self, label="&Submit task")
		self.stop = wx.Button(self, label="St&op task")
		self.stop.Disable()
		row.Add(self.submit, 0, wx.ALL, 8)
		row.Add(self.stop, 0, wx.ALL, 8)
		sizer.Add(row)
		self.status = wx.StaticText(self, label="No task is running.")
		sizer.Add(self.status, 0, wx.ALL, 8)
		self.output = labelled(self, sizer, "Codex &answer", lambda: wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2))
		self.previous = labelled(self, sizer, "&Previous tasks, press Enter to open one", lambda: wx.ListBox(self, size=(-1, 140)), False)
		self.refresh = wx.Button(self, label="&Refresh previous tasks")
		sizer.Add(self.refresh, 0, wx.ALL, 8)
		self.SetSizer(sizer)
		self.submit.Bind(wx.EVT_BUTTON, self.on_submit)
		self.stop.Bind(wx.EVT_BUTTON, self.on_stop)
		self.refresh.Bind(wx.EVT_BUTTON, lambda event: self.load())
		self.previous.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open)
		self.previous.Bind(wx.EVT_CHAR_HOOK, self.on_previous_key)

	def load(self):
		def done(result):
			self.history = result["tasks"]
			self.previous.Set([f"Task {task['id']}, {task['status_text']}, {when(task['created'])}: {task['preview']}" for task in self.history] or ["No tasks yet."])
			if result.get("running") and self.task_id is None:
				self.follow(result["running"], resume=True)

		self.window.worker.run(self.window.client.tasks, done)

	def on_previous_key(self, event):
		if event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			self.on_open(event)
		else:
			event.Skip()

	def on_open(self, event):
		index = self.previous.GetSelection()
		if index == wx.NOT_FOUND or index >= len(self.history):
			return
		task_id = self.history[index]["id"]
		if task_id == self.task_id:
			self.output.SetFocus()
			return

		def done(task):
			self.set_status(f"Showing task {task_id}, which is {task['status_text']}.")
			with TaskDialog(self.window, task) as dialog:
				dialog.ShowModal()
			self.previous.SetFocus()

		self.set_status(f"Opening task {task_id}.")
		self.window.worker.run(lambda: self.window.client.task(task_id), done)

	def set_status(self, text):
		self.status.SetLabel(text)
		self.window.set_status(text)

	def on_submit(self, event):
		prompt = self.prompt.GetValue().strip()
		if not prompt:
			self.window.show_error("Write a task first.")
			self.prompt.SetFocus()
			return
		self.submit.Disable()
		self.set_status("Submitting the task.")

		def done(task_id):
			self.prompt.SetValue("")
			self.output.SetValue("")
			self.follow(task_id)

		def failed(message):
			self.submit.Enable()
			self.set_status(message)
			self.window.show_error(message)

		self.window.worker.run(lambda: self.window.client.start(prompt), done, failed)

	def follow(self, task_id, resume=False):
		self.task_id = task_id
		self.received = 0
		self.stop_stream = False
		self.submit.Disable()
		self.stop.Enable()
		if resume:
			self.output.SetValue("")
		self.set_status(f"Codex is working on task {task_id}.")
		threading.Thread(target=self.stream, args=(task_id,), daemon=True).start()

	def stream(self, task_id):
		client = self.window.client
		details = None
		while not self.stop_stream:
			try:
				if details is None:
					details = client.settings()["details"]
				end = client.stream(task_id, self.received, details, self.on_output, lambda: self.stop_stream)
			except Unpaired as error:
				wx.CallAfter(self.window.handle_unpaired, error.message)
				return
			except ServerError:
				time.sleep(3)
				continue
			if end is not None:
				wx.CallAfter(self.finished, task_id, end)
				return
			time.sleep(1)

	def on_output(self, text, end):
		self.received = end
		wx.CallAfter(self.output.AppendText, text)

	def finished(self, task_id, end):
		self.task_id = None
		self.submit.Enable()
		self.stop.Disable()
		message = end.get("message", f"Task {task_id} finished.")
		self.set_status(message)
		self.window.notify(message)
		self.load()
		self.window.update_projects(automatic=True)

	def on_stop(self, event):
		if self.task_id is None:
			return
		task_id = self.task_id
		self.window.worker.run(lambda: self.window.client.stop(task_id), self.set_status)


class FilesPage(wx.Panel):
	def __init__(self, parent, window):
		super().__init__(parent)
		self.window = window
		self.items = []
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.list = labelled(self, sizer, "F&iles in the working folder", lambda: wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL))
		self.list.InsertColumn(0, "Path", width=460)
		self.list.InsertColumn(1, "Size", width=120)
		grid = wx.GridSizer(2, 4, 4, 4)
		buttons = [
			("&Refresh", self.load),
			("&Download file", self.on_download_file),
			("Download f&older of the selected file", self.on_download_folder),
			("Download &everything", self.on_download_all),
			("&Upload file", self.on_upload_file),
			("Upload fo&lder", self.on_upload_folder),
		]
		for label, handler in buttons:
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, lambda event, handler=handler: handler())
			grid.Add(button, 0, wx.EXPAND)
		sizer.Add(grid, 0, wx.ALL | wx.EXPAND, 8)
		self.SetSizer(sizer)

	def load(self):
		def done(result):
			self.items = result["files"]
			self.list.DeleteAllItems()
			for index, item in enumerate(self.items):
				self.list.InsertItem(index, item["path"])
				self.list.SetItem(index, 1, size_text(item["size"]))
			count = len(self.items)
			self.window.set_status(f"{count} {'file' if count == 1 else 'files'} in the working folder.")

		self.window.worker.run(self.window.client.files, done)

	def selected(self):
		index = self.list.GetFirstSelected()
		if index == -1 or index >= len(self.items):
			self.window.show_error("Select a file in the list first.")
			return None
		return self.items[index]["path"]

	def transfer(self, title, job):
		dialog = wx.ProgressDialog(title, "Starting.", maximum=1000, parent=self.window, style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME)
		state = {"cancel": False, "last": 0}

		def progress(done, total, label=""):
			if total:
				value = min(999, int(done * 1000 / total))
				if value - state["last"] >= 10 or value == 999:
					state["last"] = value
					text = label or f"{size_text(done)} of {size_text(total)}, {value // 10} percent."
					wx.CallAfter(update, value, text)
			return not state["cancel"]

		def update(value, text):
			if dialog:
				keep, skip = dialog.Update(value, text)
				if not keep:
					state["cancel"] = True

		def finish(message):
			dialog.Destroy()
			self.window.set_status(message)
			self.window.notify(message)
			self.load()

		def failed(message):
			dialog.Destroy()
			self.window.show_error(message)

		self.window.worker.run(lambda: job(progress), finish, failed)

	def on_download_file(self):
		path = self.selected()
		if not path:
			return
		with wx.FileDialog(self, "Save the file as", defaultFile=path.rsplit("/", 1)[-1], style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			destination = dialog.GetPath()

		def job(progress):
			received = self.window.client.download(path, destination, progress=progress)
			return f"Downloaded {path}, {size_text(received)}, to {destination}."

		self.transfer("Downloading", job)

	def download_folder(self, folder, default_name):
		with wx.FileDialog(self, "Save the folder as a zip file", defaultFile=default_name, wildcard="Zip files (*.zip)|*.zip", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			destination = dialog.GetPath()

		def job(progress):
			received = self.window.client.download(folder, destination, folder=True, progress=progress)
			return f"Downloaded the folder {folder or 'workspace'} as a zip file, {size_text(received)}, to {destination}."

		self.transfer("Downloading folder", job)

	def on_download_folder(self):
		path = self.selected()
		if not path:
			return
		if "/" not in path:
			self.window.show_error("The selected file is not inside a folder. Use Download everything to get the whole working folder.")
			return
		folder = path.rsplit("/", 1)[0]
		with wx.TextEntryDialog(self, "Folder to download. You can shorten the path to download a bigger folder.", "Download folder", folder) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			folder = dialog.GetValue().strip().strip("/")
		if folder:
			self.download_folder(folder, folder.rsplit("/", 1)[-1] + ".zip")

	def on_download_all(self):
		self.download_folder("", "workspace.zip")

	def on_upload_file(self):
		with wx.FileDialog(self, "Choose a file to upload", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			local = dialog.GetPath()
		limit = self.window.max_upload
		if os.path.getsize(local) > limit:
			self.window.show_error(f"The file is larger than the {gigabytes(limit)} limit, so it was not sent.")
			return
		client = self.window.client

		def job(progress):
			result = client.upload(local, os.path.basename(local), progress=progress)
			while result.get("status") == "extracting":
				time.sleep(2)
				result = client.upload_status(result["id"])
			return result["message"]

		self.transfer("Uploading", job)

	def on_upload_folder(self):
		with wx.DirDialog(self, "Choose a folder to upload", style=wx.DD_DIR_MUST_EXIST) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			local = Path(dialog.GetPath())
		limit = self.window.max_upload
		files = []
		too_big = []
		for directory, subdirectories, names in os.walk(local):
			subdirectories[:] = [name for name in subdirectories if name not in SKIPPED_FOLDERS]
			for name in names:
				full = Path(directory) / name
				if full.is_symlink():
					continue
				if full.stat().st_size > limit:
					too_big.append(str(full.relative_to(local)))
					continue
				files.append(full)
		if not files:
			self.window.show_error("The folder has no files to upload.")
			return
		total = sum(path.stat().st_size for path in files)
		question = (
			f"Upload {len(files)} files, {size_text(total)}, from {local.name} into the folder {local.name} on the server? "
			"Files that already exist there are replaced, and archives inside the folder are not extracted. "
			f"These folders are skipped: {', '.join(sorted(SKIPPED_FOLDERS))}."
		)
		if wx.MessageBox(question, "Upload folder", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return
		client = self.window.client

		def job(progress):
			sent_before = 0
			for number, path in enumerate(files, 1):
				relative = path.relative_to(local)
				folder = "/".join((local.name,) + relative.parts[:-1])
				size = path.stat().st_size
				label = f"File {number} of {len(files)}: {relative.as_posix()}"

				def step(sent, file_total, base=sent_before, label=label):
					return progress(base + sent, total, label)

				client.upload(str(path), path.name, folder=folder, overwrite=True, extract=False, progress=step)
				sent_before += size
				if not progress(sent_before, total, label):
					raise ServerError("The upload was cancelled.")
			message = f"Uploaded {len(files)} files from {local.name}."
			if too_big:
				message += f" {len(too_big)} files were skipped because they are larger than {gigabytes(limit)}."
			return message

		self.transfer("Uploading folder", job)


class RepoDialog(wx.Dialog):
	def __init__(self, parent, result):
		super().__init__(parent, title=f"Key created for {result['name']}")
		self.result = result
		sizer = wx.BoxSizer(wx.VERTICAL)
		steps = wx.StaticText(self, label=(
			"The key was created. Copy the public key, open the GitHub page, paste the key into the Key field, "
			"tick Allow write access if Codex should push changes, then select Add key."
		))
		steps.Wrap(480)
		sizer.Add(steps, 0, wx.ALL, 8)
		self.key = labelled(self, sizer, "Public &key", lambda: wx.TextCtrl(self, value=result["public_key"], style=wx.TE_READONLY | wx.TE_MULTILINE, size=(480, 70)), False)
		self.address = labelled(self, sizer, "&Address to give Codex", lambda: wx.TextCtrl(self, value=result["address"], style=wx.TE_READONLY), False)
		row = wx.BoxSizer(wx.HORIZONTAL)
		for label, handler in (
			("&Copy public key", lambda event: self.copy(result["public_key"], "The public key was copied.")),
			("&Open the GitHub page", lambda event: webbrowser.open(result["github_url"])),
			("Copy a&ddress", lambda event: self.copy(result["address"], "The address was copied.")),
		):
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, handler)
			row.Add(button, 0, wx.ALL, 4)
		sizer.Add(row)
		sizer.Add(wx.Button(self, wx.ID_OK, "C&lose"), 0, wx.ALL | wx.ALIGN_RIGHT, 8)
		self.SetSizerAndFit(sizer)
		self.key.SetFocus()

	def copy(self, text, message):
		if wx.TheClipboard.Open():
			wx.TheClipboard.SetData(wx.TextDataObject(text))
			wx.TheClipboard.Close()
			wx.MessageBox(message, APP_NAME, wx.OK, self)


class ReposPage(wx.Panel):
	def __init__(self, parent, window):
		super().__init__(parent)
		self.window = window
		self.repos = []
		sizer = wx.BoxSizer(wx.VERTICAL)
		intro = wx.StaticText(self, label="Each repository gets its own key, which only opens that one repository. Your GitHub account is never stored on the server.")
		intro.Wrap(600)
		sizer.Add(intro, 0, wx.ALL, 8)
		self.list = labelled(self, sizer, "&Repositories", lambda: wx.ListBox(self))
		row = wx.BoxSizer(wx.HORIZONTAL)
		for label, handler in (
			("&Add repository", self.on_add),
			("&Show key and address", self.on_show),
			("Re&move key", self.on_remove),
			("R&efresh", self.load),
		):
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, lambda event, handler=handler: handler())
			row.Add(button, 0, wx.ALL, 4)
		sizer.Add(row, 0, wx.ALL, 4)
		self.SetSizer(sizer)

	def load(self):
		def done(repos):
			self.repos = repos
			self.list.Set([f"{repo['name']}: {repo['repository']}, address {repo['address']}" for repo in repos] or ["No repositories yet."])

		self.window.worker.run(self.window.client.repos, done)

	def selected(self):
		index = self.list.GetSelection()
		if index == wx.NOT_FOUND or index >= len(self.repos):
			self.window.show_error("Select a repository in the list first.")
			return None
		return self.repos[index]

	def on_add(self):
		with wx.TextEntryDialog(self, "Short name, using lowercase letters, digits and hyphens, for example myproject.", "Add repository") as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			name = dialog.GetValue().strip()
		with wx.TextEntryDialog(self, "GitHub repository as owner/name, or paste its GitHub address.", "Add repository") as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			repository = dialog.GetValue().strip()

		def done(result):
			self.load()
			with RepoDialog(self.window, result) as shown:
				shown.ShowModal()

		self.window.worker.run(lambda: self.window.client.add_repo(name, repository), done)

	def on_show(self):
		repo = self.selected()
		if not repo:
			return
		result = dict(repo, github_url=f"https://github.com/{repo['repository']}/settings/keys/new")
		with RepoDialog(self.window, result) as shown:
			shown.SetTitle(f"Key for {repo['name']}")
			shown.ShowModal()

	def on_remove(self):
		repo = self.selected()
		if not repo:
			return
		if wx.MessageBox(f"Remove the key for {repo['name']}? Codex will no longer be able to reach {repo['repository']}.", "Remove key", wx.YES_NO | wx.ICON_WARNING, self) != wx.YES:
			return

		def done(result):
			self.load()
			if wx.MessageBox(result["message"] + " Open the GitHub page now?", APP_NAME, wx.YES_NO, self) == wx.YES:
				webbrowser.open(result["github_url"])

		self.window.worker.run(lambda: self.window.client.remove_repo(repo["name"]), done)


class LogPage(wx.Panel):
	def __init__(self, parent, window):
		super().__init__(parent)
		self.window = window
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.list = labelled(self, sizer, "&Log, newest first", lambda: wx.ListBox(self))
		refresh = wx.Button(self, label="&Refresh")
		refresh.Bind(wx.EVT_BUTTON, lambda event: self.load())
		sizer.Add(refresh, 0, wx.ALL, 8)
		self.SetSizer(sizer)

	def load(self):
		def done(events):
			self.list.Set([f"{when(event['ts'])}, {event['kind'].replace('_', ' ')}: {event['detail']}" for event in events] or ["The log is empty."])

		self.window.worker.run(self.window.client.log, done)


OPTION_LABELS = (
	("model", "&Model"),
	("effort", "&Thinking level"),
	("speed", "S&peed"),
	("summary", "Thinking s&ummaries, shown only with technical details"),
	("verbosity", "Answer &length"),
	("personality", "Perso&nality"),
)


class SettingsPage(wx.Panel):
	def __init__(self, parent, window):
		super().__init__(parent)
		self.window = window
		self.values = {}
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.details = wx.CheckBox(self, label="Show technical &details in Codex answers")
		sizer.Add(self.details, 0, wx.ALL, 8)
		help_text = wx.StaticText(self, label=(
			"When this is on, the answer also shows the session number, the commands Codex runs with their output, "
			"and the number of tokens used. When it is off, you only see what Codex writes to you, and errors."
		))
		help_text.Wrap(600)
		sizer.Add(help_text, 0, wx.ALL, 8)
		self.choices = {}
		for name, label in OPTION_LABELS:
			self.choices[name] = labelled(self, sizer, label, lambda: wx.Choice(self), False)
		note = wx.StaticText(self, label=(
			"The Codex choices apply to new tasks, and a running task keeps the choices it started with. "
			"Higher thinking levels and Fast speed can use more of your usage limit. All settings are shared with the website."
		))
		note.Wrap(600)
		sizer.Add(note, 0, wx.ALL, 8)
		row = wx.BoxSizer(wx.HORIZONTAL)
		self.save = wx.Button(self, label="&Save settings")
		self.save.Bind(wx.EVT_BUTTON, self.on_save)
		reload_button = wx.Button(self, label="&Reload settings")
		reload_button.Bind(wx.EVT_BUTTON, lambda event: self.load())
		row.Add(self.save, 0, wx.ALL, 4)
		row.Add(reload_button, 0, wx.ALL, 4)
		sizer.Add(row, 0, wx.ALL, 4)
		sizer.Add(wx.StaticLine(self), 0, wx.EXPAND | wx.ALL, 8)
		local_help = wx.StaticText(self, label=(
			"Local projects are folders on this computer where you cloned a GitHub repository that Codex works on. "
			"When a task finishes, the app brings the new changes from GitHub into these folders, so you do not have to clone again. "
			"These settings are saved only on this computer, and they take effect straight away."
		))
		local_help.Wrap(600)
		sizer.Add(local_help, 0, wx.ALL, 8)
		self.automatic = wx.CheckBox(self, label="&When a task finishes, update the local projects")
		self.automatic.Bind(wx.EVT_CHECKBOX, self.on_automatic)
		sizer.Add(self.automatic, 0, wx.ALL, 8)
		self.folders = labelled(self, sizer, "Local pro&jects", lambda: wx.ListBox(self, size=(-1, 100)), False)
		local_row = wx.BoxSizer(wx.HORIZONTAL)
		for label, handler in (
			("&Add folder", self.on_add_folder),
			("Remo&ve folder", self.on_remove_folder),
			("Update n&ow", lambda event: self.window.update_projects(automatic=False)),
		):
			button = wx.Button(self, label=label)
			button.Bind(wx.EVT_BUTTON, handler)
			local_row.Add(button, 0, wx.ALL, 4)
		sizer.Add(local_row, 0, wx.ALL, 4)
		self.SetSizer(sizer)
		self.show_projects()

	def show_projects(self):
		settings = self.window.projects.load()
		self.automatic.SetValue(settings["automatic"])
		self.folders.Set(settings["folders"] or ["No local projects yet."])

	def change_projects(self, change):
		settings = self.window.projects.load()
		change(settings)
		try:
			self.window.projects.save(settings)
		except OSError as error:
			self.window.show_error(f"The local projects could not be saved on this computer: {error}")
		self.show_projects()

	def on_automatic(self, event):
		value = self.automatic.GetValue()
		self.change_projects(lambda settings: settings.update(automatic=value))
		self.window.set_status("Local projects are updated when a task finishes." if value else "Local projects are only updated when you select Update now.")

	def on_add_folder(self, event):
		with wx.DirDialog(self, "Choose the folder of a cloned repository", style=wx.DD_DIR_MUST_EXIST) as dialog:
			if dialog.ShowModal() != wx.ID_OK:
				return
			folder = dialog.GetPath()
		if not is_repository(folder):
			self.window.show_error(f"{folder} is not a Git repository, so it was not added. Choose the folder you cloned from GitHub, the one that contains the hidden .git folder.")
			return
		if folder in self.window.projects.load()["folders"]:
			self.window.show_error(f"{folder} is already in the list.")
			return
		self.change_projects(lambda settings: settings["folders"].append(folder))
		self.folders.SetSelection(len(self.window.projects.load()["folders"]) - 1)
		self.window.set_status(f"{folder} was added to the local projects.")

	def on_remove_folder(self, event):
		folders = self.window.projects.load()["folders"]
		index = self.folders.GetSelection()
		if index == wx.NOT_FOUND or index >= len(folders):
			self.window.show_error("Select a folder in the list first.")
			return
		folder = folders[index]
		self.change_projects(lambda settings: settings["folders"].remove(folder))
		self.window.set_status(f"{folder} was removed from the local projects. The folder itself was not deleted.")

	def show(self, result):
		self.details.SetValue(bool(result["details"]))
		options = result.get("options") or {}
		for name, choice in self.choices.items():
			entries = result.get("choices", {}).get(name) or [{"value": "", "label": "Default"}]
			self.values[name] = [entry["value"] for entry in entries]
			choice.Set([entry["label"] for entry in entries])
			current = options.get(name, "")
			choice.SetSelection(self.values[name].index(current) if current in self.values[name] else 0)
		if not result.get("models_available", True):
			self.window.set_status("The list of models could not be loaded from Codex, so only the current choices are shown.")
		self.Layout()

	def load(self):
		self.window.worker.run(self.window.client.settings, self.show)

	def on_save(self, event):
		details = self.details.GetValue()
		options = {}
		for name, choice in self.choices.items():
			index = choice.GetSelection()
			values = self.values.get(name, [])
			options[name] = values[index] if 0 <= index < len(values) else ""
		self.save.Disable()

		def done(result):
			self.save.Enable()
			self.show(result)
			self.window.set_status(result["message"])
			wx.MessageBox(result["message"], APP_NAME, wx.OK | wx.ICON_INFORMATION, self)

		def failed(message):
			self.save.Enable()
			self.window.show_error(message)

		self.window.worker.run(lambda: self.window.client.save_settings(details, options), done, failed)


class MainWindow(wx.Frame):
	def __init__(self, client):
		super().__init__(None, title=APP_NAME, size=(900, 700))
		self.client = client
		self.max_upload = MAX_UPLOAD
		self.projects = Projects()
		self.updating = False
		self.worker = Worker(self)
		self.CreateStatusBar()
		menu = wx.MenuBar()
		file_menu = wx.Menu()
		unpair = file_menu.Append(wx.ID_ANY, "&Unpair this computer")
		exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tAlt+F4")
		menu.Append(file_menu, "&File")
		self.SetMenuBar(menu)
		self.Bind(wx.EVT_MENU, self.on_unpair, unpair)
		self.Bind(wx.EVT_MENU, lambda event: self.Close(), exit_item)
		self.notebook = wx.Notebook(self)
		self.tasks = TasksPage(self.notebook, self)
		self.files = FilesPage(self.notebook, self)
		self.repos = ReposPage(self.notebook, self)
		self.log = LogPage(self.notebook, self)
		self.settings = SettingsPage(self.notebook, self)
		for page, label in ((self.tasks, "Tasks"), (self.files, "Files"), (self.repos, "Repositories"), (self.log, "Log"), (self.settings, "Settings")):
			self.notebook.AddPage(page, label)
		self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_page)
		self.loaded = set()
		self.Bind(wx.EVT_CLOSE, self.on_close)
		self.check_connection()

	def check_connection(self):
		def done(status):
			self.max_upload = status.get("max_upload") or MAX_UPLOAD
			self.set_status(f"Connected as {status['device']}.")
			self.load_page(0)

		self.worker.run(self.client.status, done)

	def on_page(self, event):
		self.load_page(event.GetSelection())
		event.Skip()

	def load_page(self, index):
		page = self.notebook.GetPage(index)
		if index not in self.loaded:
			self.loaded.add(index)
			page.load()

	def set_status(self, text):
		self.SetStatusText(text)

	def show_error(self, message):
		self.set_status(message)
		wx.MessageBox(message, APP_NAME, wx.OK | wx.ICON_ERROR, self)

	def notify(self, message):
		winsound.MessageBeep(winsound.MB_ICONASTERISK)
		if not self.IsActive():
			notification = wx.adv.NotificationMessage(APP_NAME, message, parent=self)
			notification.Show(timeout=wx.adv.NotificationMessage.Timeout_Auto)
			self.RequestUserAttention()

	def update_projects(self, automatic):
		settings = self.projects.load()
		if automatic and not (settings["automatic"] and settings["folders"]):
			return
		if not settings["folders"]:
			self.show_error("There are no local projects yet. Add one in the Settings tab first.")
			return
		if self.updating:
			self.set_status("The local projects are already being updated.")
			return
		self.updating = True
		self.set_status("Updating the local projects from GitHub.")

		def done(result):
			self.updating = False
			text, important = result
			self.set_status(text)
			if important or not automatic:
				if not self.IsActive():
					self.notify(text)
				wx.MessageBox(text, "Local projects", wx.OK | wx.ICON_INFORMATION, self)

		def failed(message):
			self.updating = False
			self.show_error(message)

		self.worker.run(lambda: update_all(settings["folders"]), done, failed)

	def handle_unpaired(self, message):
		Pairing().forget()
		wx.MessageBox(message + " The app will now ask for a new pairing code.", APP_NAME, wx.OK | wx.ICON_WARNING, self)
		self.Destroy()
		wx.CallAfter(start_pairing)

	def on_unpair(self, event):
		if wx.MessageBox("Unpair this computer? You will need a new pairing code from the website to use the app again.", APP_NAME, wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
			return

		def done(result):
			Pairing().forget()
			wx.MessageBox("This computer was unpaired.", APP_NAME, wx.OK, self)
			self.Destroy()

		self.worker.run(self.client.unpair, done)

	def on_close(self, event):
		self.tasks.stop_stream = True
		self.Destroy()


def start_pairing():
	with PairDialog(None) as dialog:
		if dialog.ShowModal() != wx.ID_OK:
			wx.GetApp().ExitMainLoop()
			return
		client = dialog.result
	MainWindow(client).Show()


def main():
	app = wx.App()
	app.SetAppName(APP_NAME)
	saved = Pairing().load()
	if saved:
		MainWindow(Client(saved["server"], saved["token"])).Show()
	else:
		start_pairing()
	app.MainLoop()
