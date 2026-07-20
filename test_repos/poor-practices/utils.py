def function1(a, b, c, d, e, f, g):
    result = a + b + c + d + e + f + g
    return result


def function2():
    x = 1
    y = 2
    z = 3
    a = 4
    b = 5
    # more variables...
    return x + y + z + a + b


# Copy pasted from stackoverflow
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
