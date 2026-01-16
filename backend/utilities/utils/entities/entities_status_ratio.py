def ratio_distribution(base_distribution, num_entities):
    """
    Distributes a total number of entities across different statuses based on percentage weights.

    Args:
        base_distribution (dict): A dictionary where keys are status names (str) and values are
            percentages (int or float) representing the desired distribution. The total should
            ideally sum to 100, but the function handles any sum proportionally.
        num_entities (int): The total number of entities to distribute.

    Returns:
        dict: A dictionary mapping each status to the number of entities assigned to it.
              The total will always sum to `num_entities`.

    Notes:
        - Handles rounding and ensures the total count remains exact.
        - In case of rounding errors, it distributes the remainder to the statuses with the
          largest fractional parts to maintain fairness.

    Example:
        >>> base_distribution = {
        ...     'ACTIVE': 70,
        ...     'ON_HOLD': 10,
        ...     'PENDING': 5,
        ...     'SUSPENDED': 10,
        ...     'INACTIVE': 5
        ... }
        >>> ratio_distribution(base_distribution, 1000)
        {'ACTIVE': 700, 'ON_HOLD': 100, 'PENDING': 50, 'SUSPENDED': 100, 'INACTIVE': 50}

    """
    base_total = sum(base_distribution.values())

    # Initial proportional allocation (floored)
    distribution = {
        status: round((count / base_total) * num_entities)
        for status, count in base_distribution.items()
    }

    # Adjust for rounding error
    diff = num_entities - sum(distribution.values())
    if diff != 0:
        remainders = {
            status: ((base_distribution[status] / base_total) * num_entities) - distribution[status]
            for status in base_distribution
        }
        sorted_statuses = sorted(remainders.items(), key=lambda x: x[1], reverse=True)

        for i in range(abs(diff)):
            status = sorted_statuses[i % len(sorted_statuses)][0]
            distribution[status] += 1 if diff > 0 else -1

    return distribution
