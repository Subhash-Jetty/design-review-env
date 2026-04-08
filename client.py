from typing import Optional

try:
    from openenv.core.env_client import EnvClient
except ImportError:
    # Fallback for standalone usage
    class EnvClient:
        action_type = None
        observation_type = None
        state_type = None
        def __init__(self, *args, **kwargs):
            pass

from .models import ReviewAction, ReviewObservation, ReviewState


class ReviewEnv(EnvClient):
    """
    Client interface for the Design Review AI Environment.

    Connects to the isolated server containing the engineering
    simulation, design catalog, and grading engine.

    Usage (async):
        async with ReviewEnv(base_url="http://localhost:8000") as client:
            obs = await client.reset()
            result = await client.step(ReviewAction(action_type="inspect", component_id="member_1"))

    Usage (sync):
        with ReviewEnv(base_url="http://localhost:8000").sync() as client:
            obs = client.reset()
            result = client.step(ReviewAction(action_type="inspect", component_id="member_1"))
    """

    action_type = ReviewAction
    observation_type = ReviewObservation
    state_type = ReviewState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
