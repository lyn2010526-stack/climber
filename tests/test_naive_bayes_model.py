"""Tests for naive_bayes model."""

import pytest

from app.ml.models.naive_bayes_model import (
    NaiveBayesModel,
    NaiveBayesPrediction,
)


class TestNaiveBayesModel:
    """Tests for model."""

    @pytest.mark.asyncio
    async def test_train_and_predict(self):
        model = NaiveBayesModel()
        X = [[1.0, 2.0], [3.0, 4.0]]
        y = ['positive', 'negative']
        metrics = await model.train(X, y)
        assert model.is_trained is True
        assert metrics.accuracy > 0

    @pytest.mark.asyncio
    async def test_predict(self):
        model = NaiveBayesModel()
        await model.train([[1.0]], ['pos'])
        pred = await model.predict([1.0])
        assert isinstance(pred, NaiveBayesPrediction)
        assert 0 <= pred.confidence <= 1
