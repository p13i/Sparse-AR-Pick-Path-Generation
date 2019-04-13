def return_list_of_tuples(func):
    def inner(*args, **kwargs):
        return_value = func(*args, **kwargs)
        return [tuple(point) for point in return_value]

    return inner


def return_tuple(func):
    def inner(*args, **kwargs):
        return_value = func(*args, **kwargs)
        return tuple(return_value)

    return inner
