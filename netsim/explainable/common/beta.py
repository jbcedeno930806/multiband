def linear_beta(start, end, steps):
    def call(n):
        return max(start + n * (end - start) / (steps - 1), end)

    return call
