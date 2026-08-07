"""Tests for recommendation ML module."""


from app.ml.recommendation_ml import (
    RecommendationClassifier,
    RecommendationCluster,
    RecommendationCrossValidator,
    RecommendationEncoder,
    RecommendationFeatureSelector,
    RecommendationMatrix,
    RecommendationRegression,
    RecommendationScaler,
    RecommendationVector,
)


class TestRecommendationVector:
    """Tests for vector operations."""

    def test_addition(self):
        v1 = RecommendationVector([1, 2, 3])
        v2 = RecommendationVector([4, 5, 6])
        result = v1 + v2
        assert result.data == [5, 7, 9]

    def test_dot_product(self):
        v1 = RecommendationVector([1, 2, 3])
        v2 = RecommendationVector([4, 5, 6])
        assert v1.dot(v2) == 32

    def test_magnitude(self):
        v = RecommendationVector([3, 4])
        assert v.magnitude() == 5.0

    def test_normalize(self):
        v = RecommendationVector([3, 4])
        normalized = v.normalize()
        assert abs(normalized.magnitude() - 1.0) < 1e-10

    def test_cosine_similarity(self):
        v1 = RecommendationVector([1, 0])
        v2 = RecommendationVector([0, 1])
        assert abs(v1.cosine_similarity(v2)) < 1e-10

    def test_euclidean_distance(self):
        v1 = RecommendationVector([0, 0])
        v2 = RecommendationVector([3, 4])
        assert v1.euclidean_distance(v2) == 5.0


class TestRecommendationMatrix:
    """Tests for matrix operations."""

    def test_shape(self):
        m = RecommendationMatrix([[1, 2], [3, 4]])
        assert m.shape == (2, 2)

    def test_transpose(self):
        m = RecommendationMatrix([[1, 2], [3, 4]])
        t = m.transpose()
        assert t.rows == [[1, 3], [2, 4]]

    def test_multiply(self):
        m1 = RecommendationMatrix([[1, 2], [3, 4]])
        m2 = RecommendationMatrix([[5, 6], [7, 8]])
        result = m1.multiply(m2)
        assert result.rows == [[19, 22], [43, 50]]


class TestRecommendationScaler:
    """Tests for feature scaling."""

    def test_min_max_scale(self):
        result = RecommendationScaler.min_max_scale([1, 2, 3], 0, 1)
        assert result == [0.0, 0.5, 1.0]

    def test_standardize(self):
        result = RecommendationScaler.standardize([1, 2, 3, 4, 5])
        assert abs(sum(result)) < 1e-10

    def test_empty_input(self):
        assert RecommendationScaler.min_max_scale([]) == []


class TestRecommendationEncoder:
    """Tests for encoding."""

    def test_one_hot_encode(self):
        result = RecommendationEncoder.one_hot_encode(2, 4)
        assert result == [0, 0, 1, 0]

    def test_label_encode(self):
        result = RecommendationEncoder.label_encode(["a", "b", "a", "c"])
        assert result == [0, 1, 0, 2]

    def test_frequency_encode(self):
        result = RecommendationEncoder.frequency_encode(["a", "b", "a"])
        assert result[0] == 2 / 3

    def test_binary_encode(self):
        result = RecommendationEncoder.binary_encode(5, 4)
        assert result == [1, 0, 1, 0]


class TestRecommendationClassifier:
    """Tests for classifiers."""

    def test_knn_classify(self):
        train = [[0, 0], [1, 1], [5, 5], [6, 6]]
        labels = [0, 0, 1, 1]
        result = RecommendationClassifier.knn_classify(train, labels, [0.5, 0.5], k=3)
        assert result == 0


class TestRecommendationCluster:
    """Tests for clustering."""

    def test_kmeans(self):
        data = [[0, 0], [1, 0], [0, 1], [10, 10], [11, 10], [10, 11]]
        labels, centroids = RecommendationCluster.kmeans(data, k=2)
        assert len(centroids) == 2
        assert len(labels) == 6

    def test_dbscan(self):
        data = [[0, 0], [1, 0], [0, 1], [10, 10]]
        labels = RecommendationCluster.dbscan(data, eps=2, min_pts=2)
        assert len(labels) == 4


class TestRecommendationRegression:
    """Tests for regression."""

    def test_linear_regression(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        slope, intercept = RecommendationRegression.linear_regression(x, y)
        assert abs(slope - 2.0) < 1e-10
        assert abs(intercept) < 1e-10

    def test_r_squared(self):
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        r2 = RecommendationRegression.r_squared(x, y, 2.0, 0.0)
        assert abs(r2 - 1.0) < 1e-10


class TestRecommendationFeatureSelector:
    """Tests for feature selection."""

    def test_variance_threshold(self):
        features = [[1, 100], [1, 200], [1, 300]]
        result = RecommendationFeatureSelector.variance_threshold(features)
        assert 1 in result
        assert 0 not in result

    def test_correlation_filter(self):
        features = [[1, 2], [2, 4], [3, 6]]
        result = RecommendationFeatureSelector.correlation_filter(features, threshold=0.9)
        assert len(result) == 1


class TestRecommendationCrossValidator:
    """Tests for cross-validation."""

    def test_k_fold_split(self):
        folds = RecommendationCrossValidator.k_fold_split(10, k=5)
        assert len(folds) == 5

    def test_stratified_split(self):
        labels = [0, 0, 0, 0, 1, 1, 1, 1]
        train, test = RecommendationCrossValidator.stratified_split(labels, test_ratio=0.25)
        assert len(train) + len(test) == 8
