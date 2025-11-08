"""Tests for runner module signal handling and server execution."""

from __future__ import annotations

import signal
from unittest.mock import MagicMock, patch

from credproxy.runner import (
    run_server,
    setup_cli_logging,
    validate_config_file,
    setup_signal_handlers,
)


class TestSignalHandlers:
    """Test signal handler setup and graceful shutdown."""

    def test_setup_signal_handlers_registers_handlers(self):
        """Test that signal handlers are properly registered."""
        with patch("signal.signal") as mock_signal:
            setup_signal_handlers()

            # Verify signal.signal was called for SIGTERM and SIGINT
            assert mock_signal.call_count == 2
            # Check that the calls were made with the right signals
            calls = mock_signal.call_args_list
            signals = [call[0][0] for call in calls]
            assert signal.SIGTERM in signals
            assert signal.SIGINT in signals

    def test_setup_signal_handlers_cleanup_functionality(self):
        """Test that signal handler cleanup functionality works."""
        # Test the signal handler function directly
        with patch("sys.exit") as mock_exit:
            # Import the signal handler function by testing setup_signal_handlers
            with patch("signal.signal") as mock_signal:
                captured_handler = None

                def capture_handler(sig, handler):
                    nonlocal captured_handler
                    captured_handler = handler

                mock_signal.side_effect = capture_handler
                setup_signal_handlers()

                # Now test the captured handler
                if captured_handler:
                    # Test with no Flask app (should not crash)
                    captured_handler(signal.SIGTERM, None)
                    mock_exit.assert_called_with(0)


class TestConfigValidation:
    """Test configuration file validation."""

    @patch("credproxy.runner.Config.from_file")
    def test_validate_config_file_success(self, mock_config_from_file):
        """Test successful config file validation."""
        mock_config_from_file.return_value = MagicMock()

        result = validate_config_file("valid_config.yaml")

        assert result is True
        mock_config_from_file.assert_called_once_with("valid_config.yaml")

    @patch("credproxy.runner.Config.from_file")
    def test_validate_config_file_failure(self, mock_config_from_file):
        """Test config file validation failure."""
        mock_config_from_file.side_effect = Exception("Invalid config")

        result = validate_config_file("invalid_config.yaml")

        assert result is False
        mock_config_from_file.assert_called_once_with("invalid_config.yaml")


class TestCliLogging:
    """Test CLI logging setup."""

    def test_setup_cli_logging_info(self):
        """Test setting up CLI logging to INFO level."""
        with patch("credproxy.runner.LOG") as mock_log:
            mock_handler = MagicMock()
            mock_log.handlers = [mock_handler]

            setup_cli_logging("INFO")

            mock_log.setLevel.assert_called_once()
            mock_handler.setLevel.assert_called_once()

    def test_setup_cli_logging_debug(self):
        """Test setting up CLI logging to DEBUG level."""
        with patch("credproxy.runner.LOG") as mock_log:
            mock_handler = MagicMock()
            mock_log.handlers = [mock_handler]

            setup_cli_logging("DEBUG")

            mock_log.setLevel.assert_called_once()
            mock_handler.setLevel.assert_called_once()

    def test_setup_cli_logging_multiple_handlers(self):
        """Test setting up CLI logging with multiple handlers."""
        with patch("credproxy.runner.LOG") as mock_log:
            mock_handler1 = MagicMock()
            mock_handler2 = MagicMock()
            mock_log.handlers = [mock_handler1, mock_handler2]

            setup_cli_logging("WARNING")

            mock_log.setLevel.assert_called_once()
            mock_handler1.setLevel.assert_called_once()
            mock_handler2.setLevel.assert_called_once()


class TestRunServer:
    """Test run_server function."""

    @patch("credproxy.runner.init_app")
    @patch("credproxy.runner.Config.from_file")
    @patch("credproxy.runner.setup_signal_handlers")
    def test_run_server_success(
        self, mock_setup_signals, mock_config_from_file, mock_init_app
    ):
        """Test successful server run."""
        # Setup mocks
        mock_args = MagicMock()
        mock_args.config = "test_config.yaml"
        mock_args.dev = False

        mock_config = MagicMock()
        mock_config.server.host = "localhost"
        mock_config.server.port = 8080
        mock_config.server.debug = False
        mock_config_from_file.return_value = mock_config

        mock_app = MagicMock()
        mock_init_app.return_value = mock_app

        # Mock app.run to avoid actually starting server
        mock_app.run = MagicMock()

        result = run_server(mock_args)

        assert result == 0
        mock_setup_signals.assert_called_once()
        mock_config_from_file.assert_called_once_with("test_config.yaml")
        mock_init_app.assert_called_once_with(mock_config)
        mock_app.run.assert_called_once_with(host="localhost", port=8080, debug=False)

    @patch("credproxy.runner.init_app")
    @patch("credproxy.runner.Config.from_file")
    @patch("credproxy.runner.setup_signal_handlers")
    def test_run_server_with_dev_flag(
        self, mock_setup_signals, mock_config_from_file, mock_init_app
    ):
        """Test server run with dev flag overriding config debug."""
        mock_args = MagicMock()
        mock_args.config = "test_config.yaml"
        mock_args.dev = True

        mock_config = MagicMock()
        mock_config.server.host = "localhost"
        mock_config.server.port = 8080
        mock_config.server.debug = False  # Config debug is False
        mock_config_from_file.return_value = mock_config

        mock_app = MagicMock()
        mock_init_app.return_value = mock_app
        mock_app.run = MagicMock()

        result = run_server(mock_args)

        assert result == 0
        # Debug should be True due to --dev flag
        mock_app.run.assert_called_once_with(host="localhost", port=8080, debug=True)

    @patch("credproxy.runner.init_app")
    @patch("credproxy.runner.Config.from_file")
    @patch("credproxy.runner.setup_signal_handlers")
    def test_run_server_keyboard_interrupt(
        self, mock_setup_signals, mock_config_from_file, mock_init_app
    ):
        """Test server run handles KeyboardInterrupt."""
        mock_args = MagicMock()
        mock_args.config = "test_config.yaml"
        mock_args.dev = False

        mock_config = MagicMock()
        mock_config.server.host = "localhost"
        mock_config.server.port = 8080
        mock_config.server.debug = False
        mock_config_from_file.return_value = mock_config

        mock_app = MagicMock()
        mock_init_app.return_value = mock_app
        mock_app.run.side_effect = KeyboardInterrupt()

        result = run_server(mock_args)

        assert result == 0

    @patch("credproxy.runner.init_app")
    @patch("credproxy.runner.Config.from_file")
    @patch("credproxy.runner.setup_signal_handlers")
    def test_run_server_general_exception(
        self, mock_setup_signals, mock_config_from_file, mock_init_app
    ):
        """Test server run handles general exceptions."""
        mock_args = MagicMock()
        mock_args.config = "test_config.yaml"
        mock_args.dev = False

        mock_config = MagicMock()
        mock_config.server.host = "localhost"
        mock_config.server.port = 8080
        mock_config.server.debug = False
        mock_config_from_file.return_value = mock_config

        mock_app = MagicMock()
        mock_init_app.return_value = mock_app
        mock_app.run.side_effect = Exception("Server error")

        result = run_server(mock_args)

        assert result == 1

    @patch("credproxy.runner.Config.from_file")
    @patch("credproxy.runner.setup_signal_handlers")
    def test_run_server_config_error(self, mock_setup_signals, mock_config_from_file):
        """Test server run handles config loading errors."""
        mock_args = MagicMock()
        mock_args.config = "nonexistent.yaml"
        mock_args.dev = False

        mock_config_from_file.side_effect = FileNotFoundError("Config not found")

        result = run_server(mock_args)

        assert result == 1
        mock_setup_signals.assert_called_once()
        mock_config_from_file.assert_called_once_with("nonexistent.yaml")

    def test_signal_handler_duplicate_shutdown(self):
        """Test signal handler handles duplicate shutdown signals."""
        # Import the signal handler function

        # Reset global state
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler with duplicate signals
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    # First signal should set shutdown_requested and call exit
                    captured_handler(signal.SIGTERM, None)
                    assert credproxy.runner.shutdown_requested is True
                    mock_exit.assert_called_with(0)

                    # Reset mock for second call
                    mock_exit.reset_mock()

                    # Second signal should exit early (line 35->exit)
                    captured_handler(signal.SIGTERM, None)
                    # Should not call exit again since shutdown already requested
                    mock_exit.assert_not_called()

    def test_signal_handler_cleanup_exception_handling(self):
        """Test signal handler exception handling in cleanup block."""
        # Import the signal handler function
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler triggers exception handling
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    # Create a mock current_app that raises exception when accessed
                    mock_current_app = MagicMock()
                    mock_current_app.config.get.side_effect = RuntimeError(
                        "Flask cleanup error"
                    )

                    with patch("flask.current_app", mock_current_app):
                        # Should handle exception gracefully (lines 51-53)
                        captured_handler(signal.SIGTERM, None)

                        # Should still exit despite exception
                        mock_exit.assert_called_with(0)

    def test_signal_handler_no_flask_app(self):
        """Test signal handler when no Flask app is available."""
        # Import the signal handler function
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler with no Flask app
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    with patch("flask.current_app", None):
                        # Should handle missing Flask app gracefully (lines 43-46)
                        captured_handler(signal.SIGTERM, None)

                        # Should still exit despite missing Flask app
                        mock_exit.assert_called_with(0)

    def test_signal_handler_credentials_cleanup(self):
        """Test signal handler credentials cleanup (lines 45-46)."""
        # Import the signal handler function
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler with credentials cleanup
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    # Mock Flask app with credentials handler
                    mock_credentials_handler = MagicMock()
                    mock_credentials_handler.cleanup = MagicMock()

                    mock_current_app = MagicMock()
                    mock_current_app.config.get.side_effect = (
                        lambda key, default=None: {
                            "credentials_handler": mock_credentials_handler,
                            "file_watcher": None,
                        }.get(key, default)
                    )

                    with patch("flask.current_app", mock_current_app):
                        captured_handler(signal.SIGTERM, None)

                        # Verify credentials cleanup was called
                        mock_credentials_handler.cleanup.assert_called_once()
                        mock_exit.assert_called_with(0)

    def test_signal_handler_file_watcher_cleanup(self):
        """Test signal handler file watcher cleanup (lines 48-50)."""
        # Import the signal handler function
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler with file watcher cleanup
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    # Mock Flask app with file watcher
                    mock_file_watcher = MagicMock()
                    mock_file_watcher.stop = MagicMock()

                    mock_current_app = MagicMock()
                    mock_current_app.config.get.side_effect = (
                        lambda key, default=None: {
                            "credentials_handler": None,
                            "file_watcher": mock_file_watcher,
                        }.get(key, default)
                    )

                    with patch("flask.current_app", mock_current_app):
                        captured_handler(signal.SIGTERM, None)

                        # Verify file watcher cleanup was called
                        mock_file_watcher.stop.assert_called_once()
                        mock_exit.assert_called_with(0)

    def test_signal_handler_both_components_cleanup(self):
        """Test signal handler cleanup of both components (lines 45-50)."""
        # Import the signal handler function
        import credproxy.runner

        credproxy.runner.shutdown_requested = False

        # Get the signal handler by calling setup_signal_handlers
        with patch("signal.signal") as mock_signal:
            captured_handler = None

            def capture_handler(sig, handler):
                nonlocal captured_handler
                captured_handler = handler

            mock_signal.side_effect = capture_handler
            setup_signal_handlers()

            # Now test the captured handler with both components
            if captured_handler:
                with patch("sys.exit") as mock_exit:
                    # Mock Flask app with both components
                    mock_credentials_handler = MagicMock()
                    mock_credentials_handler.cleanup = MagicMock()

                    mock_file_watcher = MagicMock()
                    mock_file_watcher.stop = MagicMock()

                    mock_current_app = MagicMock()
                    mock_current_app.config.get.side_effect = (
                        lambda key, default=None: {
                            "credentials_handler": mock_credentials_handler,
                            "file_watcher": mock_file_watcher,
                        }.get(key, default)
                    )

                    with patch("flask.current_app", mock_current_app):
                        captured_handler(signal.SIGTERM, None)

                        # Verify both cleanups were called
                        mock_credentials_handler.cleanup.assert_called_once()
                        mock_file_watcher.stop.assert_called_once()
                        mock_exit.assert_called_with(0)
