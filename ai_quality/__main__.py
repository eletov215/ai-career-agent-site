from pathlib import Path
import argparse
from .ai006 import run_gate

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path)
args = parser.parse_args()
result = run_gate(args.output_dir)
print(result["status"])
raise SystemExit(result["status"] != "passed")
