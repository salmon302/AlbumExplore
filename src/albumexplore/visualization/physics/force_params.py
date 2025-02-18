from dataclasses import dataclass
import math

@dataclass
class ForceParams:
	gravity: float = 0.00005  # Reduced for less movement
	repulsion: float = 15.0   # Further reduced for better stability
	attraction: float = 0.002  # Reduced for smoother movement
	damping: float = 0.85     # Increased for better stability
	max_velocity: float = 0.2  # Reduced for smoother animation
	convergence_threshold: float = 0.008  # More aggressive convergence
	min_movement: float = 0.03  # Reduced minimum movement
	cooling_factor: float = 0.92  # More aggressive cooling
	
	@classmethod
	def adaptive(cls, node_count: int) -> 'ForceParams':
		"""Create adaptive parameters optimized for performance."""
		# Use logarithmic scaling with reduced base factor
		scale = math.log(node_count + 1) * 0.15
		
		# Adjust parameters based on graph size
		if node_count < 50:
			return cls()  # Use default values for small graphs
		elif node_count < 200:
			return cls(
				repulsion=30.0 * scale,
				attraction=0.008 / scale,
				damping=0.85,
				max_velocity=0.3,
				convergence_threshold=0.01 * scale,
				cooling_factor=0.92
			)
		else:
			return cls(
				repulsion=40.0 * scale,
				attraction=0.005 / scale,
				damping=0.9,
				max_velocity=0.15,
				convergence_threshold=0.015 * scale,
				cooling_factor=0.90
			)