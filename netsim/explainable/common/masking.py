import numpy as np


def predict_with_valid_classes(classifier, samples, valid_classes_fn):
    use_decision = hasattr(classifier, "decision_function")
    scores = (
        classifier.decision_function(samples)
        if use_decision
        else classifier.predict_proba(samples)
    )

    final_preds = []
    all_classes = classifier.classes_  # Usa las clases reales

    for i in range(len(samples)):
        valid_classes = valid_classes_fn(samples[i])
        sample_scores = np.copy(scores[i]).ravel()

        # Encontrar qué clases no son válidas
        invalid_classes = np.setdiff1d(all_classes, valid_classes)

        # Para invalidar correctamente, necesitas trabajar sobre los índices
        for cls in invalid_classes:
            idx = np.where(all_classes == cls)[0][0]
            sample_scores[idx] = -np.inf

        pred_idx = np.argmax(sample_scores)
        pred_class = all_classes[pred_idx]

        final_preds.append(pred_class)

    return final_preds


def compute_mask(env):
    n_routes = 3
    n_blocks = 5
    start = 28  # n_nodes * 2
    n_feautures = n_blocks * 2 + 3

    def _mask(sample):
        mask = []
        for idp in range(n_routes):
            for idb in range(n_blocks):
                pos = start + idp * (n_feautures) + idb * 2
                if sample[pos] != -1:
                    mask.append(idp * n_blocks + idb)
        return mask

    return _mask


def used_classes(acts):
    classes = [0] * 15
    for a in acts:
        classes[a] += 1
    # print("used classes", classes)
    c = [0] * 15
    for i, value in enumerate(classes):
        if value != 0:
            c[i] = 1
    return c


def find_nth_one_position(arreglo1, n):
    """
    Encuentra la posición del n-ésimo 1 en arreglo1.

    Args:
        arreglo1 (array-like): Arreglo de ceros y unos.
        n (int): Índice en arreglo2, o sea, el n-ésimo 1 a buscar (0-indexado).

    Returns:
        int: Posición en arreglo1 donde se encuentra el n-ésimo 1.

    Raises:
        ValueError: Si n es mayor al número de unos en arreglo1.
    """

    # Encuentra los índices donde arreglo1 == 1
    one_positions = []
    for index, value in enumerate(arreglo1):
        if value == 1:
            one_positions.append(index)

    if n > len(one_positions):
        raise ValueError(
            f"El arreglo1 solo tiene {len(one_positions)} unos, no existe el índice {n}."
        )

    return one_positions[n - 1]
