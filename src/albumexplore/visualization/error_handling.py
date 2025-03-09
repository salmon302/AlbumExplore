from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
import traceback
import logging
from PyQt6.QtWidgets import QMessageBox, QWidget
from albumexplore.gui.gui_logging import gui_logger

class ErrorSeverity(Enum):
	INFO = "info"
	WARNING = "warning"
	ERROR = "error"
	CRITICAL = "critical"

class ErrorCategory(Enum):
	DATA = "data"
	LAYOUT = "layout"
	RENDERING = "rendering"
	INTERACTION = "interaction"
	STATE = "state"
	NETWORK = "network"
	SYSTEM = "system"

@dataclass
class ErrorContext:
	view_type: str
	operation: str
	data: Dict[str, Any]

@dataclass
class ErrorInfo:
	message: str
	severity: ErrorSeverity
	category: ErrorCategory
	context: Optional[ErrorContext]
	traceback: Optional[str] = None
	recovery_hint: Optional[str] = None

class ErrorManager:
	"""Manages error handling and user notifications."""
	
	def __init__(self):
		self.logger = logging.getLogger(__name__)
		self.error_handlers: Dict[ErrorCategory, List[callable]] = {}
		self.active_errors: List[ErrorInfo] = []
		self.last_error = None
		self._setup_logging()
	
	def _setup_logging(self) -> None:
		"""Setup logging configuration."""
		handler = logging.StreamHandler()
		formatter = logging.Formatter(
			'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
		)
		handler.setFormatter(formatter)
		self.logger.addHandler(handler)
		self.logger.setLevel(logging.INFO)
	
	def register_handler(self, category: ErrorCategory, handler: callable) -> None:
		"""Register an error handler for a specific category."""
		if category not in self.error_handlers:
			self.error_handlers[category] = []
		self.error_handlers[category].append(handler)
	
	def handle_error(self, error: Exception, context: Optional[ErrorContext] = None, parent: Optional[QWidget] = None) -> ErrorInfo:
		"""Handle an error and return error information."""
		if context is None:
			context = ErrorContext(
				view_type="unknown",
				operation="unknown",
				data={}
			)
		
		error_info = self._create_error_info(error, context)
		self.active_errors.append(error_info)
		self.last_error = error
		
		# Log the error
		self._log_error(error_info)
		gui_logger.error(f"Error occurred: {str(error)}", exc_info=True)
		
		# Call registered handlers
		if error_info.category in self.error_handlers:
			for handler in self.error_handlers[error_info.category]:
				try:
					handler(error_info)
				except Exception as e:
					self.logger.error(f"Error handler failed: {e}")
					gui_logger.error(f"Error in error handler: {str(e)}", exc_info=True)
		
		# Show error dialog if no handlers handled it
		if not self.error_handlers:
			self._show_error_dialog(error, parent)
		
		return error_info
	
	def _create_error_info(self, error: Exception, context: ErrorContext) -> ErrorInfo:
		"""Create ErrorInfo from exception and context."""
		severity = self._get_severity(error)
		category = self._get_category(error, context)
		
		return ErrorInfo(
			message=str(error),
			severity=severity,
			category=category,
			context=context,
			traceback=traceback.format_exc(),
			recovery_hint=self._get_recovery_hint(category, error)
		)
	
	def _get_severity(self, error: Exception) -> ErrorSeverity:
		"""Determine error severity based on exception type."""
		if isinstance(error, (KeyError, ValueError, TypeError)):
			return ErrorSeverity.ERROR
		elif isinstance(error, (MemoryError, SystemError)):
			return ErrorSeverity.CRITICAL
		else:
			return ErrorSeverity.WARNING
	
	def _get_category(self, error: Exception, context: Optional[ErrorContext]) -> ErrorCategory:
		"""Determine error category based on exception and context."""
		if context is None:
			return ErrorCategory.SYSTEM
			
		operation = getattr(context, 'operation', '').lower()
		view_type = getattr(context, 'view_type', '').lower()
		
		if any(term in operation for term in ["csv", "data", "parsing"]) or view_type == "data":
			return ErrorCategory.DATA
		elif "layout" in operation:
			return ErrorCategory.LAYOUT
		elif "render" in operation:
			return ErrorCategory.RENDERING
		elif "state" in operation:
			return ErrorCategory.STATE
		else:
			return ErrorCategory.SYSTEM
	
	def _get_recovery_hint(self, category: ErrorCategory, error: Exception) -> str:
		"""Get recovery hint based on error category and type."""
		if "csv" in str(error).lower():
			return "Check CSV format and file structure"
		hints = {
			ErrorCategory.LAYOUT: "Try adjusting the viewport or reducing the number of visible elements",
			ErrorCategory.RENDERING: "Try switching to a different view type or refreshing the visualization",
			ErrorCategory.DATA: "Check data format and consistency",
			ErrorCategory.STATE: "Try resetting the view state",
			ErrorCategory.SYSTEM: "Contact system administrator"
		}
		return hints.get(category, "Contact system administrator")
	
	def _log_error(self, error_info: ErrorInfo) -> None:
		"""Log error information."""
		log_message = (
			f"Error: {error_info.message}\n"
			f"Category: {error_info.category.value}\n"
			f"Severity: {error_info.severity.value}\n"
			f"Context: View={error_info.context.view_type if error_info.context else 'unknown'}, "
			f"Operation={error_info.context.operation if error_info.context else 'unknown'}\n"
			f"Recovery Hint: {error_info.recovery_hint}"
		)
		
		if error_info.severity == ErrorSeverity.CRITICAL:
			self.logger.critical(log_message)
		elif error_info.severity == ErrorSeverity.ERROR:
			self.logger.error(log_message)
		else:
			self.logger.warning(log_message)
	
	def get_active_errors(self) -> List[ErrorInfo]:
		"""Get list of active errors."""
		return self.active_errors
	
	def clear_errors(self) -> None:
		"""Clear all active errors."""
		self.active_errors.clear()
	
	def _show_error_dialog(self, error: Exception, parent: Optional[QWidget] = None) -> None:
		"""Show error dialog to user."""
		dialog = QMessageBox(parent)
		dialog.setIcon(QMessageBox.Icon.Critical)
		dialog.setWindowTitle("Error")
		dialog.setText(str(error))
		dialog.setDetailedText(traceback.format_exc())
		dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
		dialog.exec()
