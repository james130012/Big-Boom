# config_loader.py
import json
import logging

DEFAULT_API_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "default_model": "google/gemini-2.5-flash-preview",
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 180,
    "llm_temperature": 0.05,
    "llm_max_tokens": 8192,
    "max_modules_to_process_frontend": 20
}

def load_api_config(config_path="api_config.json"):
    """Loads API configuration from a JSON file, falling back to defaults."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logging.info(f"Successfully loaded API config file: {config_path}")
            # Merge with defaults, allowing user config to override
            return {**DEFAULT_API_CONFIG, **config}
    except FileNotFoundError:
        logging.warning(f"API config file '{config_path}' not found. Using default config.")
        return DEFAULT_API_CONFIG
    except json.JSONDecodeError:
        logging.warning(f"API config file '{config_path}' is malformed. Using default config.")
        return DEFAULT_API_CONFIG
    except Exception as e:
        logging.warning(f"Error loading API config file '{config_path}': {e}. Using default config.")
        return DEFAULT_API_CONFIG

if __name__ == '__main__':
    # Example usage:
    logging.basicConfig(level=logging.INFO)
    config = load_api_config()
    print(config)
    config_custom = load_api_config("non_existent_config.json") # Test fallback
    print(config_custom)