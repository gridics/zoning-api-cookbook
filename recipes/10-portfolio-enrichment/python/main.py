from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'languages' / 'python'))
from gridics_cookbook import main
raise SystemExit(main('10'))
