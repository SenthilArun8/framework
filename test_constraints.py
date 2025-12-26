"""Test that constraints properly prevent violations"""
import pytest
from world_engine.epistemic.constraints import (
    DirectorConstraint,
    DirectorConstraintViolation,
    EpistemicLayer
)


def test_director_can_observe_layer_1():
    """Director should be allowed to observe objective world"""
    assert DirectorConstraint.validate_observation(EpistemicLayer.OBJECTIVE_WORLD)


def test_director_can_observe_layer_3():
    """Director should be allowed to observe beliefs"""
    assert DirectorConstraint.validate_observation(EpistemicLayer.BELIEF_GRAPH)


def test_director_cannot_observe_layer_4():
    """Director should NOT be allowed to observe character minds directly"""
    with pytest.raises(DirectorConstraintViolation):
        DirectorConstraint.validate_observation(EpistemicLayer.CHARACTER_MIND)


def test_director_can_act_on_layer_2():
    """Director should be allowed to create information artifacts"""
    assert DirectorConstraint.validate_action(
        EpistemicLayer.INFORMATION_ARTIFACTS,
        "create_rumor"
    )


def test_director_cannot_act_on_layer_1():
    """Director should NOT be allowed to create objective facts"""
    with pytest.raises(DirectorConstraintViolation) as exc_info:
        DirectorConstraint.validate_action(
            EpistemicLayer.OBJECTIVE_WORLD,
            "create_fact"
        )
    
    assert "cannot create objective facts" in str(exc_info.value).lower()


def test_director_cannot_act_on_layer_3():
    """Director should NOT be allowed to force beliefs"""
    with pytest.raises(DirectorConstraintViolation) as exc_info:
        DirectorConstraint.validate_action(
            EpistemicLayer.BELIEF_GRAPH,
            "force_belief"
        )
    
    assert "cannot force beliefs" in str(exc_info.value).lower()


def test_director_cannot_act_on_layer_4():
    """Director should NOT be allowed to override character minds"""
    with pytest.raises(DirectorConstraintViolation) as exc_info:
        DirectorConstraint.validate_action(
            EpistemicLayer.CHARACTER_MIND,
            "set_emotion"
        )
    
    assert "cannot override character minds" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])