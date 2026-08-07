"""ML module: language_translation - Machine learning utilities."""

from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class LanguageTranslationVector:
    """Numeric vector with operations."""
    data: list[float]

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> float:
        return self.data[idx]

    def __add__(self, other: LanguageTranslationVector) -> LanguageTranslationVector:
        return LanguageTranslationVector([a + b for a, b in zip(self.data, other.data, strict=False)])

    def __sub__(self, other: LanguageTranslationVector) -> LanguageTranslationVector:
        return LanguageTranslationVector([a - b for a, b in zip(self.data, other.data, strict=False)])

    def __mul__(self, scalar: float) -> LanguageTranslationVector:
        return LanguageTranslationVector([v * scalar for v in self.data])

    def dot(self, other: LanguageTranslationVector) -> float:
        """Dot product."""
        return sum(a * b for a, b in zip(self.data, other.data, strict=False))

    def magnitude(self) -> float:
        """Vector magnitude."""
        return math.sqrt(sum(v ** 2 for v in self.data))

    def normalize(self) -> LanguageTranslationVector:
        """Normalize to unit vector."""
        mag = self.magnitude()
        if mag == 0:
            return LanguageTranslationVector([0.0] * len(self.data))
        return LanguageTranslationVector([v / mag for v in self.data])

    def cosine_similarity(self, other: LanguageTranslationVector) -> float:
        """Cosine similarity."""
        dot = self.dot(other)
        mag_product = self.magnitude() * other.magnitude()
        return dot / mag_product if mag_product > 0 else 0.0

    def euclidean_distance(self, other: LanguageTranslationVector) -> float:
        """Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(self.data, other.data, strict=False)))


@dataclass
class LanguageTranslationMatrix:
    """Simple matrix implementation."""
    rows: list[list[float]]

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.rows), len(self.rows[0]) if self.rows else 0)

    def __getitem__(self, idx: int) -> list[float]:
        return self.rows[idx]

    def transpose(self) -> LanguageTranslationMatrix:
        """Matrix transpose."""
        if not self.rows:
            return LanguageTranslationMatrix([])
        return LanguageTranslationMatrix([list(col) for col in zip(*self.rows, strict=False)])

    def multiply(self, other: LanguageTranslationMatrix) -> LanguageTranslationMatrix:
        """Matrix multiplication."""
        if not self.rows or not other.rows:
            return LanguageTranslationMatrix([])
        result = []
        other_t = other.transpose()
        for row in self.rows:
            new_row = []
            for col in other_t.rows:
                val = sum(a * b for a, b in zip(row, col, strict=False))
                new_row.append(val)
            result.append(new_row)
        return LanguageTranslationMatrix(result)


class LanguageTranslationScaler:
    """Feature scaling utilities."""

    @staticmethod
    def min_max_scale(values: list[float], min_val: float = 0, max_val: float = 1) -> list[float]:
        """Min-max scaling."""
        if not values:
            return []
        data_min = min(values)
        data_max = max(values)
        if data_max == data_min:
            return [min_val] * len(values)
        return [min_val + (v - data_min) / (data_max - data_min) * (max_val - min_val) for v in values]

    @staticmethod
    def standardize(values: list[float]) -> list[float]:
        """Z-score standardization."""
        if len(values) < 2:
            return values
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return [0.0] * len(values)
        return [(v - mean) / std for v in values]

    @staticmethod
    def robust_scale(values: list[float]) -> list[float]:
        """Robust scaling using median and IQR."""
        if len(values) < 4:
            return values
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1 = sorted_vals[n // 4]
        q3 = sorted_vals[3 * n // 4]
        median = sorted_vals[n // 2]
        iqr = q3 - q1
        if iqr == 0:
            return [0.0] * len(values)
        return [(v - median) / iqr for v in values]


class LanguageTranslationEncoder:
    """Data encoding utilities."""

    @staticmethod
    def one_hot_encode(value: int, num_classes: int) -> list[float]:
        """One-hot encoding."""
        return [1.0 if i == value else 0.0 for i in range(num_classes)]

    @staticmethod
    def label_encode(values: list[str]) -> list[int]:
        """Label encoding."""
        unique = sorted(set(values))
        mapping = {v: i for i, v in enumerate(unique)}
        return [mapping[v] for v in values]

    @staticmethod
    def frequency_encode(values: list[str]) -> list[float]:
        """Frequency encoding."""
        counter = Counter(values)
        total = len(values)
        return [counter[v] / total for v in values]

    @staticmethod
    def binary_encode(value: int, num_bits: int) -> list[int]:
        """Binary encoding."""
        return [(value >> i) & 1 for i in range(num_bits)]


class LanguageTranslationClassifier:
    """Simple classifiers."""

    @staticmethod
    def knn_classify(
        train_data: list[list[float]],
        train_labels: list[int],
        test_point: list[float],
        k: int = 3,
    ) -> int:
        """K-nearest neighbors classification."""
        distances = []
        for i, point in enumerate(train_data):
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(point, test_point, strict=False)))
            distances.append((dist, train_labels[i]))
        distances.sort(key=lambda x: x[0])
        top_k = [label for _, label in distances[:k]]
        return Counter(top_k).most_common(1)[0][0]

    @staticmethod
    def naive_bayes_predict(
        features: list[float],
        class_means: list[list[float]],
        class_vars: list[list[float]],
        class_priors: list[float],
    ) -> int:
        """Gaussian Naive Bayes prediction."""
        scores = []
        for c in range(len(class_priors)):
            log_score = math.log(class_priors[c])
            for i, feat in enumerate(features):
                mean = class_means[c][i]
                var = class_vars[c][i]
                if var > 0:
                    log_score += -0.5 * math.log(2 * math.pi * var)
                    log_score += -0.5 * ((feat - mean) ** 2) / var
            scores.append(log_score)
        return scores.index(max(scores))


class LanguageTranslationCluster:
    """Clustering algorithms."""

    @staticmethod
    def kmeans(
        data: list[list[float]],
        k: int,
        max_iters: int = 100,
        tol: float = 1e-4,
    ) -> tuple[list[int], list[list[float]]]:
        """K-means clustering."""
        if not data or k <= 0:
            return [], []
        n = len(data)
        dims = len(data[0])
        centroids = random.sample(data, min(k, n))
        labels = [0] * n

        for _ in range(max_iters):
            new_labels = []
            for point in data:
                distances = [math.sqrt(sum((a - b) ** 2 for a, b in zip(point, c, strict=False))) for c in centroids]
                new_labels.append(distances.index(min(distances)))

            new_centroids = [[0.0] * dims for _ in range(k)]
            counts = [0] * k
            for i, point in enumerate(data):
                label = new_labels[i]
                counts[label] += 1
                for d in range(dims):
                    new_centroids[label][d] += point[d]

            for c in range(k):
                if counts[c] > 0:
                    new_centroids[c] = [v / counts[c] for v in new_centroids[c]]
                else:
                    new_centroids[c] = centroids[c]

            shift = sum(math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2, strict=False))) for c1, c2 in zip(centroids, new_centroids, strict=False))
            centroids = new_centroids
            labels = new_labels
            if shift < tol:
                break

        return labels, centroids

    @staticmethod
    def dbscan(
        data: list[list[float]],
        eps: float,
        min_pts: int,
    ) -> list[int]:
        """DBSCAN clustering."""
        n = len(data)
        labels = [-1] * n
        cluster_id = 0

        def neighbors(point_idx: int) -> list[int]:
            result = []
            for i in range(n):
                if i == point_idx:
                    continue
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(data[point_idx], data[i], strict=False)))
                if dist <= eps:
                    result.append(i)
            return result

        for i in range(n):
            if labels[i] != -1:
                continue
            nbrs = neighbors(i)
            if len(nbrs) < min_pts:
                continue
            labels[i] = cluster_id
            seeds = list(nbrs)
            j = 0
            while j < len(seeds):
                q = seeds[j]
                if labels[q] == -1:
                    labels[q] = cluster_id
                if labels[q] != -1 and labels[q] != cluster_id:
                    j += 1
                    continue
                labels[q] = cluster_id
                q_nbrs = neighbors(q)
                if len(q_nbrs) >= min_pts:
                    seeds.extend([n for n in q_nbrs if n not in seeds])
                j += 1
            cluster_id += 1

        return labels


class LanguageTranslationRegression:
    """Regression algorithms."""

    @staticmethod
    def linear_regression(
        x: list[float],
        y: list[float],
    ) -> tuple[float, float]:
        """Simple linear regression (y = ax + b)."""
        n = len(x)
        if n < 2:
            return 0, 0
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y, strict=False))
        denominator = sum((xi - x_mean) ** 2 for xi in x)
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        return slope, intercept

    @staticmethod
    def predict_linear(x: float, slope: float, intercept: float) -> float:
        """Linear prediction."""
        return slope * x + intercept

    @staticmethod
    def r_squared(x: list[float], y: list[float], slope: float, intercept: float) -> float:
        """R-squared coefficient."""
        if len(y) < 2:
            return 0
        y_mean = sum(y) / len(y)
        ss_tot = sum((yi - y_mean) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y, strict=False))
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0


class LanguageTranslationFeatureSelector:
    """Feature selection utilities."""

    @staticmethod
    def variance_threshold(features: list[list[float]], threshold: float = 0.01) -> list[int]:
        """Select features above variance threshold."""
        if not features:
            return []
        num_features = len(features[0])
        selected = []
        for i in range(num_features):
            values = [row[i] for row in features]
            if len(values) > 1:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
                if variance > threshold:
                    selected.append(i)
        return selected

    @staticmethod
    def correlation_filter(features: list[list[float]], threshold: float = 0.95) -> list[int]:
        """Remove highly correlated features."""
        if not features:
            return []
        num_features = len(features[0])
        to_remove = set()
        for i in range(num_features):
            for j in range(i + 1, num_features):
                col_i = [row[i] for row in features]
                col_j = [row[j] for row in features]
                if len(col_i) > 1:
                    mean_i = sum(col_i) / len(col_i)
                    mean_j = sum(col_j) / len(col_j)
                    cov = sum((a - mean_i) * (b - mean_j) for a, b in zip(col_i, col_j, strict=False))
                    std_i = math.sqrt(sum((a - mean_i) ** 2 for a in col_i))
                    std_j = math.sqrt(sum((b - mean_j) ** 2 for b in col_j))
                    corr = cov / (std_i * std_j) if std_i > 0 and std_j > 0 else 0
                    if abs(corr) > threshold:
                        to_remove.add(j)
        return [i for i in range(num_features) if i not in to_remove]


class LanguageTranslationCrossValidator:
    """Cross-validation utilities."""

    @staticmethod
    def k_fold_split(n_samples: int, k: int = 5) -> list[tuple[list[int], list[int]]]:
        """Generate k-fold train/test indices."""
        indices = list(range(n_samples))
        fold_size = n_samples // k
        folds = []
        for i in range(k):
            start = i * fold_size
            end = start + fold_size if i < k - 1 else n_samples
            test = indices[start:end]
            train = indices[:start] + indices[end:]
            folds.append((train, test))
        return folds

    @staticmethod
    def stratified_split(
        labels: list[int],
        test_ratio: float = 0.2,
    ) -> tuple[list[int], list[int]]:
        """Stratified train/test split."""
        label_indices: dict[int, list[int]] = {}
        for i, label in enumerate(labels):
            label_indices.setdefault(label, []).append(i)
        train, test = [], []
        for indices in label_indices.values():
            n_test = max(1, int(len(indices) * test_ratio))
            test.extend(indices[:n_test])
            train.extend(indices[n_test:])
        return train, test
