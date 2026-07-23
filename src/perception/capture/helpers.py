from functools import wraps

import numpy as np


def convert_args_to_numpy(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        converted_args = [np.array(arg) if isinstance(arg, list | tuple) else arg for arg in args]
        converted_kwargs = {
            key: np.array(value) if isinstance(value, list | tuple) else value for key, value in kwargs.items()
        }
        return func(*converted_args, **converted_kwargs)

    return wrapper
