import logging
from typing import Optional, List


class LogLevel:
    """Validates and provides logging levels."""
    
    def __init__(self, level_name: str):
        self.level_name = level_name.upper()
    
    def get_level(self) -> int:
        """Get validated logging level."""
        try:
            return getattr(logging, self.level_name)
        except AttributeError:
            print(f"Invalid LOG_LEVEL '{self.level_name}', using INFO")
            return logging.INFO
    
    def get_name(self) -> str:
        """Get the effective level name."""
        try:
            getattr(logging, self.level_name)
            return self.level_name
        except AttributeError:
            return "INFO"


class LogHandlerFactory:
    """Creates logging handlers safely."""
    
    def create_console_handler(self) -> logging.StreamHandler:
        """Create console handler."""
        return logging.StreamHandler()
    
    def create_file_handler(self, filepath: str) -> Optional[logging.FileHandler]:
        """Create file handler if possible."""
        try:
            return logging.FileHandler(filepath)
        except (OSError, IOError) as e:
            print(f"Failed to create log file '{filepath}': {e}")
            return None


class NoiseReducer:
    """Reduces logging noise from third-party libraries."""
    
    def reduce_library_noise(self) -> None:
        """Set appropriate levels for noisy libraries."""
        logging.getLogger("slack_bolt").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


class LoggingConfigurator:
    """Configures application logging following single responsibility principle."""
    
    def __init__(self, level_name: str, format_string: str, log_file: Optional[str] = None):
        self.log_level = LogLevel(level_name)
        self.format_string = format_string
        self.log_file = log_file
        self.handler_factory = LogHandlerFactory()
        self.noise_reducer = NoiseReducer()
    
    def configure(self, module_name: str) -> logging.Logger:
        """Configure logging and return logger for specified module."""
        handlers = self._create_handlers()
        self._setup_basic_config(handlers)
        self.noise_reducer.reduce_library_noise()
        
        logger = logging.getLogger(module_name)
        logger.info("Logging configured - Level: %s", self.log_level.get_name())
        return logger
    
    def _create_handlers(self) -> List[logging.Handler]:
        """Create all required handlers."""
        handlers = [self.handler_factory.create_console_handler()]
        
        if self.log_file:
            file_handler = self.handler_factory.create_file_handler(self.log_file)
            if file_handler:
                handlers.append(file_handler)
        
        return handlers
    
    def _setup_basic_config(self, handlers: List[logging.Handler]) -> None:
        """Configure the root logger."""
        logging.basicConfig(
            level=self.log_level.get_level(),
            format=self.format_string,
            handlers=handlers
        ) 