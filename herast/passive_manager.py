from __future__ import annotations
import os

from herast.schemes_storage import SchemesStorage
from herast.tree.scheme import Scheme
from herast.tree.matcher import Matcher

import herast.settings.settings_manager as settings_manager

__schemes_storages : dict[str, SchemesStorage] = {}
__passive_matcher = Matcher()

def __find_python_files_in_folder(folder: str):
	import glob
	for file_path in glob.iglob(folder + '/**/**.py', recursive=True):
		yield file_path

def __initialize():
	storage_files = set(settings_manager.get_storages_files())
	for folder in settings_manager.get_storages_folders():
		storage_files.update(__find_python_files_in_folder(folder))

	for storage_path in storage_files:
		__add_storage_file(storage_path)

def __get_storage_status_text(storage_path: str) -> str:
	globally = settings_manager.get_storage_status(storage_path, globally=True) == "enabled"
	in_idb = settings_manager.get_storage_status(storage_path, in_idb=True) == "enabled"
	if globally and in_idb:
		status = "Enabled globally and in IDB"
	elif globally:
		status = "Enabled globally"
	elif in_idb:
		status = "Enabled in IDB"
	else:
		status = "Disabled"
	return status

def __add_storages_folder(storages_folder_path: str):
	for file_path in __find_python_files_in_folder(storages_folder_path):
		__add_storage_file(file_path)

def __add_storage_file(storage_path: str):
	new_storage = SchemesStorage(storage_path)
	__schemes_storages[storage_path] = new_storage
	__load_storage(new_storage)

def __unload_storage(storage: SchemesStorage):
	for name, _ in storage.get_schemes():
		__passive_matcher.remove_scheme(name)
	storage.unload_module()

def __load_storage(storage: SchemesStorage) -> bool:
	if settings_manager.get_storage_status(storage.path) == "enabled":
		if not storage.load_module():
			return False

		storage.enabled = True
		storage.status_text = __get_storage_status_text(storage.path)
		for name, scheme in storage.get_schemes():
			__passive_matcher.add_scheme(name, scheme)
	return True



"""PUBLIC API"""

def get_passive_matcher() -> Matcher:
	"""Get matcher, that automatically matches in every decompilation."""
	return __passive_matcher

def register_storage_scheme(name:str, scheme:Scheme):
	"""API for storages to export their schemes.

	:param name: unique identificator for a scheme
	:return: call status
	"""

	if not isinstance(scheme, Scheme):
		print(scheme, "is not insance of Scheme")
		return False

	if __passive_matcher.get_scheme(name) is not None:
		print(name, "scheme already exists, skipping")
		return False

	import inspect
	storage_path = inspect.stack()[1].filename
	storage = get_storage(storage_path)
	if storage is None:
		print("Internal error, failed to find storage when registering new scheme")
		return False

	storage.add_scheme(name, scheme)
	__passive_matcher.add_scheme(name, scheme)
	return True

def get_storage(filename: str) -> SchemesStorage|None:
	"""Get storage by its path."""
	return __schemes_storages.get(filename)

def get_storages() -> list[SchemesStorage]:
	"""Get all storages."""
	return [s for s in __schemes_storages.values()]

def get_storages_folders(in_idb=False, globally=False) -> list[str]:
	"""Get all storages folders.

	:param in_idb: get only IDB storages folders
	:param globally: get only global storages folders
	"""
	return settings_manager.get_storages_folders(in_idb=in_idb, globally=globally)

def get_storages_files_from_folder(folder:str ) -> list[str]:
	"""
	"""

	if folder not in settings_manager.get_storages_folders():
		print("No such folder in settings")
		return []

	storages_filenames = []
	for file_path in __find_python_files_in_folder(folder):
		if get_storage(file_path) is not None:
			storages_filenames.append(file_path)
	return storages_filenames

def is_storage_enabled(storage_path: str) -> bool:
	"""
	"""

	storage = get_storage(storage_path)
	if storage is None:
		print("No such storage", storage_path)
		return False

	return storage.enabled

def get_enabled_storages() -> list[SchemesStorage]:
	"""Get only enabled storages."""
	return [s for s in __schemes_storages.values() if s.enabled]

def get_schemes():
	"""Get dict {scheme_name -> scheme)"""
	return dict(__passive_matcher.schemes)


def disable_storage(storage_path: str) -> bool:
	"""Change status of a storage to not export schemes to passive matcher."""
	storage = get_storage(storage_path)
	if storage is None:
		print("No such storage", storage_path)
		return False

	if not storage.enabled:
		print(storage_path, "is already disabled")
		return False

	storage.enabled = False
	settings_manager.disable_storage(storage_path)
	for name, _ in storage.get_schemes():
		__passive_matcher.remove_scheme(name)

	storage.status_text = __get_storage_status_text(storage.path)
	return True

def enable_storage(storage_path: str) -> bool:
	"""Change status of a storage to export schemes to passive matcher."""
	storage = get_storage(storage_path)
	if storage is None:
		print("No such storage", storage_path)
		return False

	if storage.enabled:
		print(storage_path, "is already enabled")
		return False

	if storage.error:
		print(storage_path, "is errored, reload first")
		return False

	if not storage.is_loaded() and not storage.load_module():
		print("Failed to load module while enabling", storage_path)
		return False

	storage.enabled = True
	settings_manager.enable_storage(storage_path)
	for name, scheme in storage.get_schemes():
		__passive_matcher.add_scheme(name, scheme)

	storage.status_text = __get_storage_status_text(storage.path)
	return True

def add_storage_folder(storages_folder: str, global_settings=False) -> bool:
	"""Add new storages from folder."""

	if storages_folder in settings_manager.get_storages_folders(globally=global_settings):
		print("Already have this folder", storages_folder)
		return False

	if not os.path.exists(storages_folder):
		print("No such folder exists", storages_folder)
		return False

	if not os.path.isdir(storages_folder):
		print(storages_folder, "is not a directory")
		return False

	settings_manager.add_storage_folder(storages_folder, globally=global_settings)
	__add_storages_folder(storages_folder)
	return True

def remove_storage_folder(storages_folder: str, global_settings=False) -> bool:
	"""Remove existing storages from folder."""

	if storages_folder not in settings_manager.get_storages_folders(globally=global_settings):
		print("No such folder", storages_folder)
		return False

	settings_manager.remove_storage_folder(storages_folder, global_settings)

	storages_files = __find_python_files_in_folder(storages_folder)
	for file_path in storages_files:
		if file_path in __schemes_storages:
			remove_storage_file(file_path)
	return True

def add_storage_file(storage_path: str, global_settings=False) -> bool:
	"""Add new storage."""

	if storage_path in settings_manager.get_storages_files(globally=global_settings):
		print("Already have this storage file", storage_path)
		return False

	if not os.path.exists(storage_path):
		print("No such file exists", storage_path)
		return False

	if not os.path.isfile(storage_path):
		print(storage_path, "is not a file")
		return False

	settings_manager.add_storage_file(storage_path, global_settings)
	__add_storage_file(storage_path)
	return True

def remove_storage_file(storage_path: str, global_settings=False) -> bool:
	"""Remove existing storage."""

	if storage_path not in settings_manager.get_storages_files(globally=global_settings):
		print("No such storage file", storage_path)
		return False

	settings_manager.remove_storage_file(storage_path, global_settings)
	storage = get_storage(storage_path)
	if storage is None:
		print("No such storage", storage_path)
		return False

	if storage.is_loaded():
		__unload_storage(storage)
	del __schemes_storages[storage_path]
	return True

def reload_storage(storage_path: str) -> bool:
	"""Reload storage module."""
	storage = get_storage(storage_path)
	if storage is None:
		print("No such storage", storage_path)
		return False

	if storage.is_loaded():
		__unload_storage(storage)

	if not __load_storage(storage):
		print("Failed to load storage on reloading", storage_path)
		return False

	storage.status_text = __get_storage_status_text(storage_path)
	return True