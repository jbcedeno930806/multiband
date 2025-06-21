import numpy as np


def get_metrics(matrix: np.ndarray):
    # Calcula métricas
    precision = np.diag(matrix) / np.sum(matrix, axis=0)
    recall = np.diag(matrix) / np.sum(matrix, axis=1)
    specificity = np.diag(matrix) / (np.sum(matrix, axis=1) - np.diag(matrix))
    f1_score = 2 * (precision * recall) / (precision + recall)

    # Imprime las métricas
    for i in range(len(precision)):
        print(f"Clase {i + 1}:")
        print(f"  Precision: {precision[i]:.4f}")
        print(f"  F1-score: {f1_score[i]:.4f}")
        print(f"  Sensibilidad (Recall): {recall[i]:.4f}")
        print(f"  Especificidad: {specificity[i]:.4f}\n")
