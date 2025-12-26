"""
Epistemic Constraints - Hard rules for system integrity

These constraints ensure the epistemic layers remain properly separated
and that no component violates the information architecture.
"""
import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class EpistemicLayer(IntEnum):
    """The four epistemic layers in order"""
    OBJECTIVE_WORLD = 1      # Ground truth
    INFORMATION_ARTIFACTS = 2  # Reports, rumors, observations
    BELIEF_GRAPH = 3          # Who believes what
    CHARACTER_MIND = 4        # Emotional interpretation


class DirectorConstraintViolation(Exception):
    """Raised when Director attempts unauthorized action"""
    pass


class DirectorConstraint:
    """
    HARD CONSTRAINT: The Director's Authority
    
    The Director may:
    - OBSERVE Layer 1 (Objective World)
    - OBSERVE Layer 3 (Belief Graph)
    - ACT on Layer 2 (Information Artifacts)
    
    The Director may NOT:
    - CREATE objective facts (Layer 1)
    - FORCE beliefs (Layer 3)
    - OVERRIDE character minds (Layer 4)
    - DECLARE outcomes
    
    The Director is an Information Architect, not a God.
    """
    
    ALLOWED_OBSERVATION_LAYERS = {
        EpistemicLayer.OBJECTIVE_WORLD,
        EpistemicLayer.BELIEF_GRAPH
    }
    
    ALLOWED_ACTION_LAYER = EpistemicLayer.INFORMATION_ARTIFACTS
    
    @staticmethod
    def validate_observation(target_layer: EpistemicLayer) -> bool:
        """
        Validate that Director is allowed to observe this layer.
        
        Args:
            target_layer: The layer being observed
            
        Returns:
            True if allowed
            
        Raises:
            DirectorConstraintViolation: If observation is not permitted
        """
        if target_layer in DirectorConstraint.ALLOWED_OBSERVATION_LAYERS:
            logger.debug(f"✓ Director observing Layer {target_layer.name}")
            return True
        
        raise DirectorConstraintViolation(
            f"Director attempted to observe Layer {target_layer.value} ({target_layer.name}). "
            f"Only Layers 1 (Objective World) and 3 (Belief Graph) may be observed."
        )
    
    @staticmethod
    def validate_action(target_layer: EpistemicLayer, action: str) -> bool:
        """
        Validate that Director is allowed to act on this layer.
        
        Args:
            target_layer: The layer being modified
            action: Description of the action
            
        Returns:
            True if allowed
            
        Raises:
            DirectorConstraintViolation: If action is not permitted
        """
        if target_layer == DirectorConstraint.ALLOWED_ACTION_LAYER:
            logger.debug(f"✓ Director acting on Layer {target_layer.name}: {action}")
            return True
        
        error_messages = {
            EpistemicLayer.OBJECTIVE_WORLD: 
                "Director cannot create objective facts. "
                "Only the simulation engine may modify Layer 1.",
            EpistemicLayer.BELIEF_GRAPH: 
                "Director cannot force beliefs. "
                "Beliefs must form naturally from information artifacts.",
            EpistemicLayer.CHARACTER_MIND: 
                "Director cannot override character minds. "
                "Characters must react based on their own traits and beliefs."
        }
        
        raise DirectorConstraintViolation(
            f"Director attempted to act on Layer {target_layer.value} ({target_layer.name}): {action}\n"
            f"{error_messages.get(target_layer, 'Invalid action.')}"
        )
    
    @staticmethod
    def validate_artifact_creation(
        artifact_type: str,
        modifies_objective_reality: bool = False
    ) -> bool:
        """
        Validate that artifact creation is legitimate.
        
        Args:
            artifact_type: Type of artifact being created
            modifies_objective_reality: Whether this artifact claims to change Layer 1
            
        Returns:
            True if valid
            
        Raises:
            DirectorConstraintViolation: If artifact is illegitimate
        """
        if modifies_objective_reality:
            raise DirectorConstraintViolation(
                f"Artifact of type '{artifact_type}' claims to modify objective reality. "
                f"Artifacts may only represent information, not create facts."
            )
        
        logger.debug(f"✓ Valid artifact creation: {artifact_type}")
        return True


class PerceptionConstraint:
    """
    Constraints for the Perception System.
    
    Ensures perception only creates artifacts based on objective facts,
    never invents information.
    """
    
    @staticmethod
    def validate_observation(
        observer_id: str,
        objective_fact_id: str,
        was_present: bool
    ) -> bool:
        """
        Validate that an observation is legitimate.
        
        Args:
            observer_id: Who is observing
            objective_fact_id: The fact being observed
            was_present: Whether observer was actually present
            
        Returns:
            True if valid
            
        Raises:
            DirectorConstraintViolation: If observation is impossible
        """
        if not was_present:
            raise DirectorConstraintViolation(
                f"Observer {observer_id} attempted to observe fact {objective_fact_id} "
                f"without being present. Perception cannot create information from nothing."
            )
        
        logger.debug(f"✓ Valid observation: {observer_id} observed {objective_fact_id}")
        return True


class BeliefConstraint:
    """
    Constraints for belief formation.
    
    Ensures beliefs are based on information artifacts,
    not created arbitrarily.
    """
    
    @staticmethod
    def validate_belief_formation(
        character_id: str,
        artifact_id: str,
        has_access_to_artifact: bool
    ) -> bool:
        """
        Validate that belief formation is legitimate.
        
        Args:
            character_id: Who is forming the belief
            artifact_id: The artifact they're basing it on
            has_access_to_artifact: Whether they actually know about the artifact
            
        Returns:
            True if valid
            
        Raises:
            DirectorConstraintViolation: If belief formation is invalid
        """
        if not has_access_to_artifact:
            raise DirectorConstraintViolation(
                f"Character {character_id} attempted to form belief about artifact {artifact_id} "
                f"without having access to it. Beliefs must be based on known information."
            )
        
        logger.debug(f"✓ Valid belief formation: {character_id} based on {artifact_id}")
        return True


# Convenience validators for common operations
def validate_director_observation(layer: int):
    """Decorator to validate Director observations"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            DirectorConstraint.validate_observation(EpistemicLayer(layer))
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def validate_director_action(layer: int, action_name: str):
    """Decorator to validate Director actions"""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            DirectorConstraint.validate_action(EpistemicLayer(layer), action_name)
            return func(self, *args, **kwargs)
        return wrapper
    return decorator