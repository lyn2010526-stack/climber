"""Tests for reinforcement model."""

import pytest

from app.ml.models.reinforcement_model import (
    ReinforcementModel,
    ReinforcementPrediction,
)


class TestReinforcementModel:
    """Tests for model."""

    @pytest.mark.asyncio
    async def test_train_and_predict(self):
        model = ReinforcementModel()
        X = [[1.0, 2.0], [3.0, 4.0]]
        y = ['positive', 'negative']
        metrics = await model.train(X, y)
        assert model.is_trained is True
        assert metrics.accuracy > 0

    @pytest.mark.asyncio
    async def test_predict(self):
        model = ReinforcementModel()
        await model.train([[1.0]], ['pos'])
        pred = await model.predict([1.0])
        assert isinstance(pred, ReinforcementPrediction)
        assert 0 <= pred.confidence <= 1
