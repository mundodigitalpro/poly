"""
Logging module for the Polymarket trading bot.

Provides professional logging with:
- Daily log file rotation (logs/bot_YYYY-MM-DD.log)
- Console output for real-time monitoring
- Configurable log levels (INFO, WARN, ERROR, DEBUG)
- Formatted timestamps and structured messages
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class BotLogger:
    """Professional logger for the trading bot."""

    def __init__(self, name: str = "PolyBot", log_level: str = "INFO"):
        """
        Initialize the bot logger.

        Args:
            name: Logger name (appears in log messages)
            log_level: Minimum log level (DEBUG, INFO, WARN, ERROR)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self._get_log_level(log_level))

        # Remove existing handlers to avoid duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Setup file handler (daily rotation by filename)
        log_filename = f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"
        log_path = log_dir / log_filename

        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File captures everything

        # Setup console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._get_log_level(log_level))

        # Create formatter
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)-5s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        self.info(f"Logger initialized: {name} (level: {log_level})")
        self.info(f"Logging to: {log_path}")

    def _get_log_level(self, level: str) -> int:
        """Convert string log level to logging constant."""
        levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARN": logging.WARNING,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return levels.get(level.upper(), logging.INFO)

    def debug(self, message: str):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str):
        """Log info message."""
        self.logger.info(message)

    def warn(self, message: str):
        """Log warning message."""
        self.logger.warning(message)

    def warning(self, message: str):
        """Alias for warn."""
        self.warn(message)

    def error(self, message: str):
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str):
        """Log critical message."""
        self.logger.critical(message)

    def separator(self, char: str = "=", length: int = 60):
        """Log a visual separator line."""
        self.info(char * length)

    def section(self, title: str):
        """Log a section header."""
        self.separator()
        self.info(title.upper().center(60))
        self.separator()


def get_logger(name: str = "PolyBot", log_level: str = "INFO") -> BotLogger:
    """
    Factory function to get a configured logger instance.

    Args:
        name: Logger name
        log_level: Minimum log level

    Returns:
        Configured BotLogger instance
    """
    return BotLogger(name, log_level)


# Example usage
if __name__ == "__main__":
    # Test the logger
    logger = get_logger("TestBot", "DEBUG")

    logger.section("Bot Started")
    logger.info("This is an info message")
    logger.debug("This is a debug message (only in file)")
    logger.warn("This is a warning message")
    logger.error("This is an error message")
    logger.separator()

    logger.info("Testing structured logging:")
    logger.info("  Balance: $18.00")
    logger.info("  Positions: 2/5")
    logger.info("  Daily P&L: +$0.45")

    logger.section("Test Complete")
