import pytest
import os
import logging
from datetime import datetime
from albumexplore.gui.gui_logging import gui_logger, log_dir

@pytest.fixture
def cleanup_logs():
	"""Clean up test logs after tests."""
	yield
	test_log = os.path.join(log_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
	if os.path.exists(test_log):
		with open(test_log, 'w') as f:
			f.write('')  # Clear contents but keep file

def test_logger_initialization():
	"""Test logger initialization and configuration."""
	assert gui_logger.name == 'gui'
	assert gui_logger.level == logging.DEBUG
	assert len(gui_logger.handlers) == 2  # File and console handlers

def test_log_directory_creation():
	"""Test log directory exists and is writable."""
	assert os.path.exists(log_dir)
	assert os.path.isdir(log_dir)
	assert os.access(log_dir, os.W_OK)

def test_log_file_creation(cleanup_logs):
	"""Test log file creation and writing."""
	test_message = "Test GUI log message"
	gui_logger.info(test_message)
	
	log_file = os.path.join(log_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
	assert os.path.exists(log_file)
	
	with open(log_file, 'r') as f:
		content = f.read()
		assert test_message in content

def test_log_levels(cleanup_logs):
	"""Test different logging levels."""
	messages = {
		'debug': "Debug message",
		'info': "Info message",
		'warning': "Warning message",
		'error': "Error message",
		'critical': "Critical message"
	}
	
	for level, msg in messages.items():
		getattr(gui_logger, level)(msg)
	
	log_file = os.path.join(log_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
	with open(log_file, 'r') as f:
		content = f.read()
		for msg in messages.values():
			assert msg in content

def test_log_formatting(cleanup_logs):
	"""Test log message formatting."""
	test_message = "Test format message"
	gui_logger.info(test_message)
	
	log_file = os.path.join(log_dir, f'gui_{datetime.now().strftime("%Y%m%d")}.log')
	with open(log_file, 'r') as f:
		content = f.read()
		# Check format components
		assert 'INFO' in content
		assert 'gui' in content
		assert test_message in content
		# Check timestamp format
		assert datetime.now().strftime("%Y-%m-%d") in content

def test_multiple_handlers():
	"""Test both file and console handlers are working."""
	assert any(isinstance(h, logging.FileHandler) for h in gui_logger.handlers)
	assert any(isinstance(h, logging.StreamHandler) for h in gui_logger.handlers)
	
	for handler in gui_logger.handlers:
		assert handler.formatter is not None