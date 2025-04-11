from typing import List
import math


def smooth_list(scalars: List[float], weight: float) -> List[float]:
    """
    EMA implementation according to
    https://github.com/tensorflow/tensorboard/blob/34877f15153e1a2087316b9952c931807a122aa7/tensorboard/components/vz_line_chart2/line-chart.ts#L699
    """
    last = 0
    smoothes = []
    num_acc = 0
    for next_val in scalars:
        smoothed, last = smooth(last, next_val, weight, num_acc)
        num_acc += 1
        smoothes.append(smoothed)
    return smoothes


def smooth(last, value, weight, num_acc):
    if num_acc == 0:
        last = 0
    last = last * weight + (1 - weight) * value
    debias_weight = 1
    if weight != 1:
        debias_weight = 1 - math.pow(weight, num_acc + 1)
    smoothed = last / debias_weight
    return smoothed, last
