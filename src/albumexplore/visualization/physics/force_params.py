"""Force parameters for physics system."""
from dataclasses import dataclass
import math

@dataclass
class ForceParams:
    """Parameters for force-directed layout."""
    # Base forces
    repulsion: float = 1000.0  # Base repulsive force between nodes
    spring_coefficient: float = 0.04  # Spring force coefficient
    gravitational_constant: float = 0.1  # Center gravity force
    boundary_force: float = 50.0  # Force from boundaries
    
    # Physics parameters
    time_step: float = 0.5  # Integration time step
    damping: float = 0.9  # Velocity damping factor
    temperature: float = 1.0  # Initial temperature for simulated annealing
    cooling_rate: float = 0.995  # Temperature cooling rate
    
    # Spring properties
    spring_length: float = 100.0  # Natural spring length
    
    # Simulation control
    min_movement: float = 0.01  # Minimum energy for simulation to continue
    max_velocity: float = 10.0  # Maximum node velocity
    max_iterations: int = 1000  # Maximum simulation iterations
    
    # Performance parameters
    theta: float = 0.8  # Barnes-Hut theta parameter
    energy_threshold: float = 0.001  # Energy convergence threshold
    
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