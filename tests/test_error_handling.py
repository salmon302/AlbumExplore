import unittest
from albumexplore.visualization.error_handling import (
	ErrorManager, ErrorContext, ErrorInfo,
	ErrorSeverity, ErrorCategory
)

class TestErrorHandling(unittest.TestCase):
	def setUp(self):
		self.error_manager = ErrorManager()
		self.test_context = ErrorContext(
			view_type="network",
			operation="layout",
			data={"node_count": 100}
		)

	def test_error_severity_classification(self):
		"""Test error severity classification."""
		# Test value error handling
		error = ValueError("Invalid value")
		error_info = self.error_manager._create_error_info(error, self.test_context)
		self.assertEqual(error_info.severity, ErrorSeverity.ERROR)
		
		# Test system error handling
		error = SystemError("Critical system error")
		error_info = self.error_manager._create_error_info(error, self.test_context)
		self.assertEqual(error_info.severity, ErrorSeverity.CRITICAL)

	def test_error_category_classification(self):
		"""Test error category classification."""
		# Test layout error
		context = ErrorContext(
			view_type="network",
			operation="layout_calculation",
			data={}
		)
		error_info = self.error_manager._create_error_info(ValueError(), context)
		self.assertEqual(error_info.category, ErrorCategory.LAYOUT)
		
		# Test data error
		context.operation = "data_processing"
		error_info = self.error_manager._create_error_info(ValueError(), context)
		self.assertEqual(error_info.category, ErrorCategory.DATA)

	def test_error_handler_registration(self):
		"""Test error handler registration and execution."""
		handler_called = {'value': False}
		
		def test_handler(error_info: ErrorInfo):
			handler_called['value'] = True
			self.assertEqual(error_info.category, ErrorCategory.LAYOUT)
		
		# Register handler
		self.error_manager.register_handler(ErrorCategory.LAYOUT, test_handler)
		
		# Trigger error
		self.error_manager.handle_error(
			ValueError("Test error"),
			ErrorContext("network", "layout", {})
		)
		
		self.assertTrue(handler_called['value'])

	def test_recovery_hints(self):
		"""Test recovery hint generation."""
		# Test layout error hint
		context = ErrorContext("network", "layout", {})
		error_info = self.error_manager.handle_error(ValueError(), context)
		self.assertIn("viewport", error_info.recovery_hint.lower())
		
		# Test rendering error hint
		context.operation = "render"
		error_info = self.error_manager.handle_error(ValueError(), context)
		self.assertIn("view type", error_info.recovery_hint.lower())

	def test_error_tracking(self):
		"""Test error tracking functionality."""
		# Generate some errors
		self.error_manager.handle_error(
			ValueError("Error 1"),
			ErrorContext("network", "layout", {})
		)
		self.error_manager.handle_error(
			TypeError("Error 2"),
			ErrorContext("table", "render", {})
		)
		
		# Check active errors
		active_errors = self.error_manager.get_active_errors()
		self.assertEqual(len(active_errors), 2)
		
		# Clear errors
		self.error_manager.clear_errors()
		self.assertEqual(len(self.error_manager.get_active_errors()), 0)

	def test_error_logging(self):
		"""Test error logging functionality."""
		with self.assertLogs(level='ERROR') as log:
			self.error_manager.handle_error(
				ValueError("Critical test error"),
				ErrorContext("network", "layout", {})
			)
			self.assertTrue(any("Critical test error" in msg for msg in log.output))

	def test_csv_parsing_errors(self):
		"""Test CSV parsing error handling."""
		# Test missing columns error
		context = ErrorContext(
			view_type="data",
			operation="csv_parsing",
			data={"file": "test.csv"}
		)
		error = ValueError("Missing required columns")
		error_info = self.error_manager._create_error_info(error, context)
		self.assertEqual(error_info.category, ErrorCategory.DATA)
		self.assertEqual(error_info.severity, ErrorSeverity.ERROR)
		
		# Test invalid data error
		error = ValueError("Invalid data format")
		error_info = self.error_manager._create_error_info(error, context)
		self.assertEqual(error_info.category, ErrorCategory.DATA)
		
		# Test recovery hints for CSV errors
		error_info = self.error_manager.handle_error(error, context)
		self.assertIn("check", error_info.recovery_hint.lower())

if __name__ == '__main__':
	unittest.main()