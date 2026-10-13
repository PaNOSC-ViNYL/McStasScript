import subprocess
import sys
import unittest


class TestPackageImport(unittest.TestCase):
    def test_root_import_does_not_load_runtime_stacks(self):
        code = """
import sys

before = set(sys.modules)
import mcstasscript
from mcstasscript import has_component, mcstas_pygen

runtime_stacks = {
    "IPython",
    "h5py",
    "ipywidgets",
    "libpyvinyl",
    "matplotlib",
    "numpy",
    "yaml",
}
loaded = sorted(
    name for name in set(sys.modules) - before
    if name.split(".", 1)[0] in runtime_stacks
)
if loaded:
    raise RuntimeError(loaded)
if not mcstasscript.__version__:
    raise RuntimeError("package version is empty")
if has_component.__name__ != "has_component":
    raise RuntimeError("lazy helper import failed")
if mcstas_pygen.__name__ != "mcstas_pygen":
    raise RuntimeError("lazy pygen import failed")
"""
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=result.stdout + result.stderr,
        )
