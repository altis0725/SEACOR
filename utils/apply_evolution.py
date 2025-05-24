import sys
import json
from utils.evolution_applier import apply_evolution
import logging

logging.basicConfig(filename='logs/task.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("使い方: python apply_evolution.py evolution_result.json")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        evo = json.load(f)
    apply_evolution(evo) 