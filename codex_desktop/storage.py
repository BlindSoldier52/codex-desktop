import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path

ENTROPY = b"codex-desktop-device-v1"
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class DataBlob(ctypes.Structure):
	_fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32
crypt32.CryptProtectData.argtypes = [
	ctypes.POINTER(DataBlob), wintypes.LPCWSTR, ctypes.POINTER(DataBlob),
	ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob),
]
crypt32.CryptProtectData.restype = wintypes.BOOL
crypt32.CryptUnprotectData.argtypes = [
	ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.POINTER(DataBlob),
	ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob),
]
crypt32.CryptUnprotectData.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = [ctypes.c_void_p]
kernel32.LocalFree.restype = ctypes.c_void_p


def blob(data):
	buffer = ctypes.create_string_buffer(data, len(data))
	return DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def read_blob(result):
	try:
		return ctypes.string_at(result.pbData, result.cbData)
	finally:
		kernel32.LocalFree(ctypes.cast(result.pbData, ctypes.c_void_p))


def protect(data):
	source, source_buffer = blob(data)
	entropy, entropy_buffer = blob(ENTROPY)
	result = DataBlob()
	if not crypt32.CryptProtectData(ctypes.byref(source), "Codex desktop", ctypes.byref(entropy), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(result)):
		raise ctypes.WinError()
	return read_blob(result)


def unprotect(data):
	source, source_buffer = blob(data)
	entropy, entropy_buffer = blob(ENTROPY)
	result = DataBlob()
	if not crypt32.CryptUnprotectData(ctypes.byref(source), None, ctypes.byref(entropy), None, None, CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(result)):
		raise ctypes.WinError()
	return read_blob(result)


class Pairing:
	def __init__(self):
		self.folder = Path(os.environ.get("APPDATA", str(Path.home()))) / "CodexDesktop"
		self.path = self.folder / "device.dat"

	def load(self):
		try:
			data = json.loads(unprotect(self.path.read_bytes()).decode("utf-8"))
		except (OSError, ValueError):
			return None
		if not isinstance(data, dict) or not data.get("server") or not data.get("token"):
			return None
		return data

	def save(self, server, token, name):
		self.folder.mkdir(parents=True, exist_ok=True)
		payload = json.dumps({"server": server, "token": token, "name": name}).encode("utf-8")
		temporary = self.path.with_suffix(".new")
		temporary.write_bytes(protect(payload))
		os.replace(temporary, self.path)

	def forget(self):
		try:
			self.path.unlink()
		except FileNotFoundError:
			pass
