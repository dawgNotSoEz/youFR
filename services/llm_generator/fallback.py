def is_model_unavailable_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "model" in message and "unavailable" in message


def pick_models(configured_models: list[str]) -> list[str]:
    return [model for model in configured_models if model and model.strip()]
