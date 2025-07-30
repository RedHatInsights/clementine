import pytest
import logging
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from clementine.config.logging import LogLevel, LogHandlerFactory, NoiseReducer, LoggingConfigurator


class TestLogLevel:
    """Test LogLevel validation functionality."""
    
    def test_valid_log_level(self):
        """Test valid logging levels."""
        log_level = LogLevel("INFO")
        
        assert log_level.get_level() == logging.INFO
        assert log_level.get_name() == "INFO"
    
    def test_lowercase_log_level(self):
        """Test that lowercase levels are converted to uppercase."""
        log_level = LogLevel("debug")
        
        assert log_level.get_level() == logging.DEBUG
        assert log_level.get_name() == "DEBUG"
    
    def test_invalid_log_level_fallback(self):
        """Test fallback to INFO for invalid levels."""
        with patch('builtins.print') as mock_print:
            log_level = LogLevel("INVALID")
            
            assert log_level.get_level() == logging.INFO
            assert log_level.get_name() == "INFO"
            mock_print.assert_called_once_with("Invalid LOG_LEVEL 'INVALID', using INFO")
    
    def test_all_valid_levels(self):
        """Test all standard logging levels."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        expected_values = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
        
        for level_name, expected_value in zip(valid_levels, expected_values):
            log_level = LogLevel(level_name)
            assert log_level.get_level() == expected_value
            assert log_level.get_name() == level_name


class TestLogHandlerFactory:
    """Test LogHandlerFactory creation methods."""
    
    def test_create_console_handler(self):
        """Test console handler creation."""
        factory = LogHandlerFactory()
        
        handler = factory.create_console_handler()
        
        assert isinstance(handler, logging.StreamHandler)
    
    def test_create_file_handler_success(self):
        """Test successful file handler creation."""
        factory = LogHandlerFactory()
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            handler = factory.create_file_handler(temp_path)
            
            assert isinstance(handler, logging.FileHandler)
            assert handler.baseFilename.endswith(os.path.basename(temp_path))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_create_file_handler_failure(self):
        """Test file handler creation failure handling."""
        factory = LogHandlerFactory()
        invalid_path = "/invalid/path/that/does/not/exist/logfile.log"
        
        with patch('builtins.print') as mock_print:
            handler = factory.create_file_handler(invalid_path)
            
            assert handler is None
            mock_print.assert_called_once()
            assert "Failed to create log file" in mock_print.call_args[0][0]
    
    def test_create_file_handler_permission_error(self):
        """Test file handler creation with permission errors."""
        factory = LogHandlerFactory()
        
        with patch('logging.FileHandler') as mock_file_handler:
            mock_file_handler.side_effect = PermissionError("Permission denied")
            
            with patch('builtins.print') as mock_print:
                handler = factory.create_file_handler("/some/path/log.txt")
                
                assert handler is None
                mock_print.assert_called_once()


class TestNoiseReducer:
    """Test NoiseReducer library management."""
    
    def test_reduce_library_noise(self):
        """Test that library loggers are set to WARNING level."""
        noise_reducer = NoiseReducer()
        
        # Store original levels
        slack_logger = logging.getLogger("slack_bolt")
        urllib_logger = logging.getLogger("urllib3")
        original_slack_level = slack_logger.level
        original_urllib_level = urllib_logger.level
        
        try:
            noise_reducer.reduce_library_noise()
            
            assert slack_logger.level == logging.WARNING
            assert urllib_logger.level == logging.WARNING
        finally:
            # Restore original levels
            slack_logger.setLevel(original_slack_level)
            urllib_logger.setLevel(original_urllib_level)


class TestLoggingConfigurator:
    """Test LoggingConfigurator orchestration with dependency injection."""
    
    def test_configure_with_console_only(self):
        """Test configuration with console handler only."""
        # Create configurator with no log file
        configurator = LoggingConfigurator(
            level_name="DEBUG",
            format_string="%(message)s",
            log_file=None
        )
        
        # Mock the components
        mock_handler_factory = Mock()
        mock_console_handler = Mock()
        mock_handler_factory.create_console_handler.return_value = mock_console_handler
        mock_handler_factory.create_file_handler.return_value = None
        
        mock_noise_reducer = Mock()
        
        # Inject dependencies
        configurator.handler_factory = mock_handler_factory
        configurator.noise_reducer = mock_noise_reducer
        
        with patch('logging.basicConfig') as mock_basic_config:
            logger = configurator.configure("test_module")
            
            # Verify handler creation
            mock_handler_factory.create_console_handler.assert_called_once()
            mock_handler_factory.create_file_handler.assert_not_called()
            
            # Verify basic config
            mock_basic_config.assert_called_once()
            call_args = mock_basic_config.call_args
            assert call_args[1]['level'] == logging.DEBUG
            assert call_args[1]['format'] == "%(message)s"
            assert mock_console_handler in call_args[1]['handlers']
            
            # Verify noise reduction
            mock_noise_reducer.reduce_library_noise.assert_called_once()
            
            # Verify logger returned
            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_module"
    
    def test_configure_with_file_handler(self):
        """Test configuration with both console and file handlers."""
        configurator = LoggingConfigurator(
            level_name="INFO",
            format_string="%(levelname)s: %(message)s",
            log_file="/path/to/logfile.log"
        )
        
        # Mock components
        mock_handler_factory = Mock()
        mock_console_handler = Mock()
        mock_file_handler = Mock()
        mock_handler_factory.create_console_handler.return_value = mock_console_handler
        mock_handler_factory.create_file_handler.return_value = mock_file_handler
        
        mock_noise_reducer = Mock()
        
        # Inject dependencies
        configurator.handler_factory = mock_handler_factory
        configurator.noise_reducer = mock_noise_reducer
        
        with patch('logging.basicConfig') as mock_basic_config:
            logger = configurator.configure("test_module")
            
            # Verify both handlers created
            mock_handler_factory.create_console_handler.assert_called_once()
            mock_handler_factory.create_file_handler.assert_called_once_with("/path/to/logfile.log")
            
            # Verify both handlers in config
            call_args = mock_basic_config.call_args
            handlers = call_args[1]['handlers']
            assert mock_console_handler in handlers
            assert mock_file_handler in handlers
            assert len(handlers) == 2
    
    def test_configure_file_handler_creation_fails(self):
        """Test configuration when file handler creation fails."""
        configurator = LoggingConfigurator(
            level_name="INFO",
            format_string="%(message)s",
            log_file="/invalid/path/logfile.log"
        )
        
        # Mock components
        mock_handler_factory = Mock()
        mock_console_handler = Mock()
        mock_handler_factory.create_console_handler.return_value = mock_console_handler
        mock_handler_factory.create_file_handler.return_value = None  # Failure
        
        mock_noise_reducer = Mock()
        
        # Inject dependencies
        configurator.handler_factory = mock_handler_factory
        configurator.noise_reducer = mock_noise_reducer
        
        with patch('logging.basicConfig') as mock_basic_config:
            logger = configurator.configure("test_module")
            
            # Should only have console handler
            call_args = mock_basic_config.call_args
            handlers = call_args[1]['handlers']
            assert mock_console_handler in handlers
            assert len(handlers) == 1
    
    def test_configure_with_invalid_log_level(self):
        """Test configuration with invalid log level."""
        configurator = LoggingConfigurator(
            level_name="INVALID_LEVEL",
            format_string="%(message)s",
            log_file=None
        )
        
        mock_handler_factory = Mock()
        mock_console_handler = Mock()
        mock_handler_factory.create_console_handler.return_value = mock_console_handler
        mock_noise_reducer = Mock()
        
        configurator.handler_factory = mock_handler_factory
        configurator.noise_reducer = mock_noise_reducer
        
        with patch('logging.basicConfig') as mock_basic_config:
            with patch('builtins.print'):  # Suppress print from LogLevel
                logger = configurator.configure("test_module")
                
                # Should fallback to INFO level
                call_args = mock_basic_config.call_args
                assert call_args[1]['level'] == logging.INFO
    
    def test_integration_with_real_components(self):
        """Test integration with real component instances."""
        # This tests the actual component integration without mocking internal components
        configurator = LoggingConfigurator(
            level_name="WARNING",
            format_string="%(name)s - %(levelname)s - %(message)s",
            log_file=None
        )
        
        # Test that real components are created and work together
        assert isinstance(configurator.log_level, LogLevel)
        assert isinstance(configurator.handler_factory, LogHandlerFactory)
        assert isinstance(configurator.noise_reducer, NoiseReducer)
        
        # Test actual configuration (though we can't easily verify logging.basicConfig)
        with patch('logging.basicConfig'):
            logger = configurator.configure("integration_test")
            assert isinstance(logger, logging.Logger)
            assert logger.name == "integration_test"


class TestLoggingConfiguratorEndToEnd:
    """End-to-end tests with minimal mocking to test real behavior."""
    
    def test_end_to_end_console_logging(self):
        """Test that console handler is created and configured properly."""
        configurator = LoggingConfigurator(
            level_name="INFO",
            format_string="TEST: %(message)s", 
            log_file=None
        )
        
        # Test the configuration creates proper handler
        handlers_before = len(logging.root.handlers)
        logger = configurator.configure("end_to_end_test")
        
        # Verify logger was created
        assert logger.name == "end_to_end_test"
        assert isinstance(logger, logging.Logger)
        
        # Test that logging level is properly configured
        assert configurator.log_level.get_level() == logging.INFO
    
    def test_end_to_end_file_logging(self):
        """Test that file handler is created when log file is specified."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            configurator = LoggingConfigurator(
                level_name="DEBUG",
                format_string="%(levelname)s: %(message)s",
                log_file=temp_path
            )
            
            # Test that file handler would be created
            file_handler = configurator.handler_factory.create_file_handler(temp_path)
            assert file_handler is not None
            assert isinstance(file_handler, logging.FileHandler)
            
            # Test configuration
            logger = configurator.configure("file_test")
            assert logger.name == "file_test"
            assert configurator.log_level.get_level() == logging.DEBUG
            
            file_handler.close()  # Clean up
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path) 