import os
import idaapi

from herast.storages_settings import StoragesSettings

def get_settings_path():
	return os.path.join(idaapi.get_user_idadir(), "herast_settings.json")

class HerastSettings(StoragesSettings):
	@classmethod
	def save_json_str(cls, saved_str):
		with open(get_settings_path(), 'w') as f:
			f.write(saved_str)

	@classmethod
	def load_json_str(cls):
		if not os.path.exists(get_settings_path()):
			print("[!] WARNING: settings file does not exist, creating empty one")
			json_str = "{}"
			cls.save_json_str(json_str)
			return json_str

		with open(get_settings_path(), 'r') as f:
			return f.read()

herast_settings = HerastSettings.create()


def get_storages_folders():
	return list(herast_settings.folders)

def get_storages_files():
	return list(herast_settings.files)