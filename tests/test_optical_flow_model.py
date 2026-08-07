"""Tests for optical_flow ML model."""


from app.ml.optical_flow_model import (
    OpticalFlowMLModel,
)


class TestOpticalFlowMLModel:
    """Tests for ML model."""

    def test_create_model(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        assert mid is not None

    def test_get_model(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        result = model.get_model(mid)
        assert result is not None
        assert result['name'] == 'test'

    def test_list_models(self):
        model = OpticalFlowMLModel()
        model.create_model('m1', 'classification')
        model.create_model('m2', 'regression')
        result = model.list_models()
        assert len(result) == 2

    def test_train_model(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        result = model.train_model(mid)
        assert result['success']

    def test_predict(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        model.train_model(mid)
        result = model.predict(mid, {'feature1': 1.0})
        assert result['success']

    def test_deploy_model(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        model.train_model(mid)
        assert model.deploy_model(mid)

    def test_archive_model(self):
        model = OpticalFlowMLModel()
        mid = model.create_model('test', 'classification')
        assert model.archive_model(mid)

    def test_get_stats(self):
        model = OpticalFlowMLModel()
        model.create_model('test', 'classification')
        stats = model.get_stats()
        assert stats['total_models'] == 1
