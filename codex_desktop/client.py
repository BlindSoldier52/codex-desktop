import http.client
import json
import os
import ssl
from urllib.parse import quote, urlencode, urlsplit

CHUNK = 1024 * 1024


class ServerError(Exception):
	def __init__(self, message, status=None):
		super().__init__(message)
		self.message = message
		self.status = status


class Unpaired(ServerError):
	pass


class Client:
	def __init__(self, server, token=None):
		parts = urlsplit(server)
		if parts.scheme != "https" or not parts.hostname:
			raise ServerError("The server address must start with https://")
		self.server = f"https://{parts.netloc}"
		self.host = parts.hostname
		self.port = parts.port or 443
		self.token = token
		self.context = ssl.create_default_context()

	def connection(self, timeout=30):
		return http.client.HTTPSConnection(self.host, self.port, timeout=timeout, context=self.context)

	def headers(self, extra=None):
		headers = {"Accept": "application/json", "User-Agent": "CodexDesktop/1.0"}
		if self.token:
			headers["Authorization"] = f"Bearer {self.token}"
		if extra:
			headers.update(extra)
		return headers

	def check(self, response):
		if 200 <= response.status < 300:
			return
		body = response.read()
		try:
			message = json.loads(body).get("message")
		except ValueError:
			message = None
		if response.status == 413 and not message:
			message = "The file is larger than the server's upload limit, so it was not accepted."
		message = message or f"The server answered with an error ({response.status})."
		if response.status == 401:
			raise Unpaired(message, 401)
		raise ServerError(message, response.status)

	def request(self, method, path, data=None, timeout=30):
		body = None
		extra = {}
		if data is not None:
			body = json.dumps(data).encode("utf-8")
			extra["Content-Type"] = "application/json"
		connection = self.connection(timeout)
		try:
			connection.request(method, path, body=body, headers=self.headers(extra))
			response = connection.getresponse()
			self.check(response)
			payload = response.read()
			return json.loads(payload) if payload else {}
		except (OSError, http.client.HTTPException) as error:
			raise ServerError(f"Could not reach the server: {error}") from error
		finally:
			connection.close()

	def pair(self, code, name):
		result = self.request("POST", "/api/pair", {"code": code, "name": name})
		self.token = result["token"]
		return result

	def status(self):
		return self.request("GET", "/api/status")

	def unpair(self):
		return self.request("DELETE", "/api/device")

	def tasks(self):
		return self.request("GET", "/api/tasks")

	def task(self, task_id):
		return self.request("GET", f"/api/tasks/{task_id}")

	def settings(self):
		return self.request("GET", "/api/settings")

	def save_settings(self, details, options):
		return self.request("PUT", "/api/settings", {"details": details, "options": options})

	def start(self, prompt):
		return self.request("POST", "/api/tasks", {"prompt": prompt})["id"]

	def stop(self, task_id):
		return self.request("POST", f"/api/tasks/{task_id}/stop")["message"]

	def stream(self, task_id, offset, details, on_output, should_stop):
		connection = self.connection(timeout=120)
		try:
			connection.request("GET", f"/api/tasks/{task_id}/stream?offset={offset}&details={int(details)}", headers=self.headers({"Accept": "text/event-stream"}))
			response = connection.getresponse()
			self.check(response)
			event = None
			while not should_stop():
				line = response.readline()
				if not line:
					return None
				line = line.decode("utf-8", "replace").rstrip("\r\n")
				if line.startswith("event: "):
					event = line[7:]
				elif line.startswith("data: "):
					data = json.loads(line[6:])
					if event == "output":
						on_output(data["text"], data["end"])
					elif event == "end":
						return data
		except (OSError, http.client.HTTPException, ValueError) as error:
			raise ServerError(f"The connection to the server was interrupted: {error}") from error
		finally:
			connection.close()

	def files(self):
		return self.request("GET", "/api/files")

	def repos(self):
		return self.request("GET", "/api/repos")["repos"]

	def add_repo(self, name, repository):
		return self.request("POST", "/api/repos", {"name": name, "repository": repository})

	def remove_repo(self, name):
		return self.request("DELETE", f"/api/repos/{quote(name)}")

	def log(self):
		return self.request("GET", "/api/log")["events"]

	def upload_status(self, upload_id):
		return self.request("GET", f"/api/uploads/{upload_id}")

	def upload(self, local_path, name, folder="", overwrite=False, extract=True, progress=None):
		size = os.path.getsize(local_path)
		query = urlencode({"name": name, "folder": folder, "overwrite": int(overwrite), "extract": int(extract)})
		connection = self.connection(timeout=300)
		try:
			connection.putrequest("PUT", f"/api/upload?{query}")
			for key, value in self.headers({"Content-Length": str(size), "Content-Type": "application/octet-stream"}).items():
				connection.putheader(key, value)
			connection.endheaders()
			sent = 0
			with open(local_path, "rb") as handle:
				while True:
					chunk = handle.read(CHUNK)
					if not chunk:
						break
					connection.send(chunk)
					sent += len(chunk)
					if progress and not progress(sent, size):
						raise ServerError("The upload was cancelled.")
			response = connection.getresponse()
			self.check(response)
			return json.loads(response.read())
		except (OSError, http.client.HTTPException) as error:
			raise ServerError(f"The upload was interrupted: {error}") from error
		finally:
			connection.close()

	def download(self, path, destination, folder=False, progress=None):
		route = "/api/files/folder" if folder else "/api/files/download"
		connection = self.connection(timeout=600)
		temporary = destination + ".part"
		try:
			connection.request("GET", f"{route}?path={quote(path)}", headers=self.headers({"Accept": "*/*"}))
			response = connection.getresponse()
			self.check(response)
			total = int(response.getheader("Content-Length") or 0)
			received = 0
			with open(temporary, "wb") as handle:
				while True:
					chunk = response.read(CHUNK)
					if not chunk:
						break
					handle.write(chunk)
					received += len(chunk)
					if progress and not progress(received, total):
						raise ServerError("The download was cancelled.")
			os.replace(temporary, destination)
			return received
		except (OSError, http.client.HTTPException) as error:
			raise ServerError(f"The download was interrupted: {error}") from error
		finally:
			connection.close()
			if os.path.exists(temporary):
				os.unlink(temporary)
