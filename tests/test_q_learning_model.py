"""Tests for q_learning model."""

import pytest

from app.ml.models.q_learning_model import (
    QLearningModel,
    QLearningPrediction,
)


class TestQLearningModel:
    """Tests for model."""

    @pytest.mark.asyncio
    async def test_train_and_predict(self):
        model = QLearningModel()
        X = [[1.0, 2.0], [3.0, 4.0]]
        y = ['positive', 'negative']
        metrics = await model.train(X, y)
        assert model.is_trained is True
        assert metrics.accuracy > 0

    @pytest.mark.asyncio
    async def test_predict(self):
        model = QLearningModel()
        await model.train([[1.0]], ['pos'])
        pred = await model.predict([1.0])
        assert isinstance(pred, QLearningPrediction)
        assert 0 <= pred.confidence <= 1
