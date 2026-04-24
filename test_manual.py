import runpy
import sys
from pathlib import Path


if __name__ == "__main__":
	sys.path.insert(0, str(Path(__file__).parent / "generar_para_email"))
	runpy.run_path(
		str(Path(__file__).parent / "generar_para_email" / "test_manual_tickets.py"),
		run_name="__main__",
	)
