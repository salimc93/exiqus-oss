def solve(matrix, k):
    n = len(matrix)
    dp = [[0] * n for _ in range(n)]

    for i in range(n):
        for j in range(n):
            if i == 0 and j == 0:
                dp[i][j] = matrix[i][j]
            elif i == 0:
                dp[i][j] = dp[i][j - 1] + matrix[i][j]
            elif j == 0:
                dp[i][j] = dp[i - 1][j] + matrix[i][j]
            else:
                dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + matrix[i][j]

    return dp[n - 1][n - 1] % k


def optimize(arr, constraints):
    result = []
    temp = sorted(enumerate(arr), key=lambda x: x[1])

    for idx, val in temp:
        if check_constraint(val, constraints):
            result.append((idx, val))

    return result[: constraints["max_items"]]


def check_constraint(val, constraints):
    return constraints["min"] <= val <= constraints["max"]
