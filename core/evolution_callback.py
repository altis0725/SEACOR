from utils.evolution_applier import apply_evolution
import logging

def evolution_callback(result, *args, **kwargs):
    try:
        # Pydanticモデル（EvolutionOutput）ならdict化
        if hasattr(result, 'model_dump'):
            evo = result.model_dump()
        elif isinstance(result, dict):
            evo = result
        else:
            import json
            evo = json.loads(result)
        apply_evolution(evo)
        logging.info("[進化案自動適用] 適用成功")
    except Exception as e:
        logging.error(f"[進化案自動適用エラー] {e}")
    return result 