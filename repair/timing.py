import time

calls = {}
average_time = {}


def average_timing(f):
    """a wrapper to stop the time of a single function.
    It's not directly logged, instead, over many calls an average is calculated."""

    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        if f.__name__ in calls:
            average_time[f.__name__] = (average_time[f.__name__] * calls[f.__name__] + (time2 - time1) * 1000.0) / (
                    calls[f.__name__] + 1)
            calls[f.__name__] += 1
        else:
            calls[f.__name__] = 1
            average_time[f.__name__] = (time2 - time1) * 1000.0
        return ret

    return wrap


def clear_average_times():
    """Resets the average times."""
    calls.clear()
    average_time.clear()


def log_average_times():
    """Used to print out the logged average times."""
    for key in calls.keys():
        print('{:s} function took {:.5f} ms on average in {} calls'.format(key, average_time[key], calls[key]))
