from abc import ABC

class Backend(ABC):
    """Abstract base class for all backends in MSB-architecture.
    
    Serves as a universal interface for numerical, visualization, or other backends.
    Concrete implementations (e.g., BackendCalculations, BackendVisualizations) must
    inherit from this class and define domain-specific methods.
    """
    pass