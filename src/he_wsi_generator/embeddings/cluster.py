def cluster_embeddings(embeddings, n_clusters: int, max_iter: int = 20) -> dict:
    numpy = _import_numpy()
    array = numpy.asarray(embeddings, dtype=numpy.float32)
    if array.ndim != 2:
        raise ValueError("embeddings must be a 2D array")
    if array.shape[0] == 0:
        raise ValueError("embeddings must contain at least one row")
    if not isinstance(n_clusters, int) or n_clusters <= 0:
        raise ValueError("n_clusters must be a positive integer")
    if n_clusters > array.shape[0]:
        raise ValueError("n_clusters cannot exceed embedding row count")
    if not isinstance(max_iter, int) or max_iter <= 0:
        raise ValueError("max_iter must be a positive integer")
    if not numpy.isfinite(array).all():
        raise ValueError("embeddings contain non-finite values")

    centers = array[:n_clusters].copy()
    labels = numpy.zeros(array.shape[0], dtype=numpy.int64)
    for _ in range(max_iter):
        distances = ((array[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        if numpy.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels = new_labels
        for cluster_id in range(n_clusters):
            members = array[labels == cluster_id]
            if members.size:
                centers[cluster_id] = members.mean(axis=0)

    final_distances = ((array - centers[labels]) ** 2).sum(axis=1)
    counts = {
        str(cluster_id): int((labels == cluster_id).sum())
        for cluster_id in range(n_clusters)
    }
    return {
        "n_clusters": n_clusters,
        "labels": [int(value) for value in labels.tolist()],
        "cluster_counts": counts,
        "inertia": float(final_distances.sum()),
        "embedding_count": int(array.shape[0]),
        "embedding_dim": int(array.shape[1]),
    }


def _import_numpy():
    try:
        import numpy
    except ImportError as exc:
        raise RuntimeError("Embedding clustering requires numpy") from exc
    return numpy
