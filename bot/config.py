"""
Configuration loader for the Polymarket trading bot.
Loads and provides access to settings from config.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict


class BotConfig:
    """Manages bot configuration from config.json and environment variables."""

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the config manager.
        
        Args:
            config_path: Path to the JSON configuration file.
        """
        self.config_path = Path(config_path)
        self.settings: Dict[str, Any] = {}
        self.load_config()

    def load_config(self):
        """Loads configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.settings = json.load(f)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using a dot-separated path (e.g., 'capital.total').
        
        Args:
            key_path: Dot-separated path to the setting.
            default: Default value if key is not found.
        """
        keys = key_path.split('.')
        value = self.settings
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    @property
    def dry_run(self) -> bool:
        return self.get("bot.dry_run", True)

    @property
    def log_level(self) -> str:
        return self.get("bot.log_level", "INFO")


def load_bot_config(config_path: str = "config.json") -> BotConfig:
    """Factory function to load configuration."""
    return BotConfig(config_path)


# Example usage
if __name__ == "__main__":
    config = load_bot_config()
    print(f"Total Capital: {config.get('capital.total')}")
    print(f"Dry Run: {config.dry_run}")
