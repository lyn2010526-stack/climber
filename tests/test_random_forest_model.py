"""Tests for random_forest model."""

import pytest

from app.ml.models.random_forest_model import (
    RandomForestModel,
    RandomForestPrediction,
)


class TestRandomForestModel:
    """Tests for model."""

    @pytest.mark.asyncio
    async def test_train_and_predict(self):
        model = RandomForestModel()
        X = [[1.0, 2.0], [3.0, 4.0]]
        y = ['positive', 'negative']
        metrics = await model.train(X, y)
        assert model.is_trained is True
        assert metrics.accuracy > 0

    @pytest.mark.asyncio
    async def test_predict(self):
        model = RandomForestModel()
        await model.train([[1.0]], ['pos'])
        pred = await model.predict([1.0])
        assert isinstance(pred, RandomForestPrediction)
        assert 0 <= pred.confidence <= 1
