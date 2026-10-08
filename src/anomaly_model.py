from sklearn.ensemble import IsolationForest


def create_isolation_forest():
    """Create the Isolation Forest model."""

    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )

    return model
def train_isolation_forest(model, feature_matrix):
    """Train the Isolation Forest model on aircraft features."""

    model.fit(feature_matrix)

    return model
def generate_anomaly_scores(model, feature_matrix):
    """Generate anomaly scores for aircraft observations."""

    scores = model.decision_function(feature_matrix)

    return scores
def generate_anomaly_predictions(model, feature_matrix):
    """Generate normal/anomaly predictions."""

    predictions = model.predict(feature_matrix)

    return predictions