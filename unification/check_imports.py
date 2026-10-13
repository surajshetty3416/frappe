"""Import every module of the four layers. Run it from a bench's sites/ folder:

	PYTHONPATH=<this repo> <bench>/env/bin/python <this repo>/unification/check_imports.py
"""

import importlib
import pkgutil
import sys

import frappe


def broken_modules():
	for layer in ("web", "analytics", "ai", "ui"):
		package = importlib.import_module(f"frappe.{layer}")
		for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
			if ".test" in module.name or module.name.endswith("__main__"):
				continue
			try:
				importlib.import_module(module.name)
			except Exception as error:
				yield f"{module.name}: {error!r}"


if __name__ == "__main__":
	frappe.init(site="", sites_path=".")
	broken = list(broken_modules())
	print("\n".join(broken) or f"Every layer module imports ({frappe.__file__}).")
	sys.exit(1 if broken else 0)
