import sys
import json
from utils.evolution_applier import apply_evolution
import logging
import os
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    LOG_FILE = os.environ.get("LOG_FILE", "logs/task.log")
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    if len(sys.argv) < 2:
        logging.error("使い方: python apply_evolution.py evolution_result.json")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        evo = json.load(f)
    apply_evolution(evo) 