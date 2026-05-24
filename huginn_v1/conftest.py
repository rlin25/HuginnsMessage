import sys
from pathlib import Path

# Ensure the huginn_v1 project root is on sys.path for all pytest runs
sys.path.insert(0, str(Path(__file__).parent))
