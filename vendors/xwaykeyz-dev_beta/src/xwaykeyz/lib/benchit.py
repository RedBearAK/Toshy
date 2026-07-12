import time


def benchit(fn):
    def fni(*args,**kwargs):
        a = time.perf_counter_ns()
        res = fn(*args, **kwargs)
        b = time.perf_counter_ns()
        tm = (b - a) // 1000
        units = "us"
        # if tm > 5000:
        #     tm = round(tm / 1000, 1)
        #     units = "ms"
        print(fn.__name__, tm, units)
        return res

    return fni
