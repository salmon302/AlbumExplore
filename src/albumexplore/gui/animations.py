from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QPointF, QObject, pyqtProperty
from PyQt6.QtWidgets import QGraphicsItem

class NodeAnimation(QObject):
	"""Handles node animation for transitions."""
	def __init__(self, item: QGraphicsItem):
		super().__init__()
		self._item = item
		self._pos = QPointF(0, 0)
		if hasattr(self._item, 'data') and isinstance(self._item.data, dict):
			self._pos = QPointF(self._item.data.get('x', 0), self._item.data.get('y', 0))
		self._opacity = 1.0
	
	def _get_pos(self) -> QPointF:
		return self._pos
	
	def _set_pos(self, pos: QPointF):
		self._pos = pos
		if hasattr(self._item, 'data'):
			if not isinstance(self._item.data, dict):
				self._item.data = {}
			self._item.data['x'] = pos.x()
			self._item.data['y'] = pos.y()
			if hasattr(self._item, 'pos'):
				if callable(self._item.pos):
					self._item.pos = lambda: {'x': pos.x(), 'y': pos.y()}
				else:
					self._item.pos = {'x': pos.x(), 'y': pos.y()}
	
	def _get_opacity(self) -> float:
		return self._opacity
	
	def _set_opacity(self, opacity: float):
		self._opacity = opacity
	
	pos = pyqtProperty(QPointF, _get_pos, _set_pos)
	opacity = pyqtProperty(float, _get_opacity, _set_opacity)

class ViewTransitionAnimator:
	"""Manages view transition animations with improved smoothing."""
	def __init__(self):
		self.animations = []
		self._animation_cache = {}
		self._default_easing = "OutCubic"
	
	def morph_nodes(self, items: dict, target_positions: dict, duration: int, easing: str = None) -> None:
		"""Animate nodes with improved smoothing."""
		self.clear()
		easing = easing or self._default_easing
		
		# Group animations for better performance
		animations_group = []
		
		for node_id, item in items.items():
			if node_id in target_positions:
				target_pos = target_positions[node_id]
				anim = NodeAnimation(item)
				
				# Position animation with improved smoothing
				pos_anim = QPropertyAnimation(anim, b"pos")
				pos_anim.setDuration(duration)
				
				# Get current position with fallback
				current_pos = QPointF(
					item.data.get('x', 0) if isinstance(item.data, dict) else 0,
					item.data.get('y', 0) if isinstance(item.data, dict) else 0
				)
				
				# Smooth start position using cache
				if node_id in self._animation_cache:
					cached_pos = self._animation_cache[node_id]
					current_pos = QPointF(
						cached_pos['x'] + (current_pos.x() - cached_pos['x']) * 0.7,
						cached_pos['y'] + (current_pos.y() - cached_pos['y']) * 0.7
					)
				
				pos_anim.setStartValue(current_pos)
				pos_anim.setEndValue(QPointF(target_pos['x'], target_pos['y']))
				
				# Use custom easing curve for smoother animation
				if easing == 'cubic-bezier(0.4, 0.0, 0.2, 1)':
					curve = QEasingCurve(QEasingCurve.Type.OutCubic)
					curve.setPeriod(0.5)
					curve.setAmplitude(1.0)
					pos_anim.setEasingCurve(curve)
				else:
					pos_anim.setEasingCurve(getattr(QEasingCurve, easing))
				
				animations_group.append(pos_anim)
				
				# Cache target position for next animation
				self._animation_cache[node_id] = target_pos
		
		# Start all animations together
		self.animations.extend(animations_group)
		for anim in animations_group:
			anim.start()
	
	def fade_nodes(self, items: dict, fade_out: bool, duration: int, easing: str = None) -> None:
		"""Animate nodes with smooth fading."""
		self.clear()
		
		animations_group = []
		for item in items.values():
			anim = NodeAnimation(item)
			opacity_anim = QPropertyAnimation(anim, b"opacity")
			opacity_anim.setDuration(duration)
			
			# Smooth opacity transition
			opacity_anim.setStartValue(0.0 if not fade_out else 1.0)
			opacity_anim.setEndValue(1.0 if not fade_out else 0.0)
			
			# Use custom easing for smoother fade
			curve = QEasingCurve(QEasingCurve.Type.InOutCubic)
			curve.setPeriod(0.5)
			opacity_anim.setEasingCurve(curve)
			
			animations_group.append(opacity_anim)
		
		# Start all animations together
		self.animations.extend(animations_group)
		for anim in animations_group:
			anim.start()
	
	def clear(self) -> None:
		"""Stop animations but preserve cache."""
		for anim in self.animations:
			anim.stop()
		self.animations.clear()
		# Don't clear cache to maintain position history