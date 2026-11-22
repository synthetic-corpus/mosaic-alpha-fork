import numpy as np


def codeboxSSIM(target_np, candidate_np):
    """
    Codebox tile likeness on a 0.0 to 1.0 scale.

    The loop is TileFitter.__get_tile_diff from mosaic.py, without the
    bail-out. That sum is 0 for an exact match and larger as the colors
    diverge. Dividing by the largest possible sum and subtracting from
    1 flips it: 1.0 is a perfect match and 0.0 is the worst match.
    """
    target = np.asarray(target_np).reshape(-1, 3)
    candidate = np.asarray(candidate_np).reshape(-1, 3)

    diff = 0
    for i in range(len(target)):
        diff += ((int(target[i][0]) - int(candidate[i][0]))**2 +
                 (int(target[i][1]) - int(candidate[i][1]))**2 +
                 (int(target[i][2]) - int(candidate[i][2]))**2)
    max_diff = len(target) * 3 * (255 ** 2)
    return 1.0 - (diff / max_diff)
