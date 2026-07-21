# xwaykeyz/models/timeout_rule.py
#
# A single conditional timeout override, in the same spirit as Modmap:
# the non-conditional default lives in the _TIMEOUTS dict, while any number of
# conditional TimeoutRule instances carry a `when` predicate plus one or more
# timeout values. Only the values explicitly passed are stored; everything else
# stays None to mean "no opinion for this key, fall through to the default".


class TimeoutRule:
    def __init__(self, name, values, when=None):
        self.name = name
        self.values = values            # dict of {timeout_key: float}, sparse
        self.conditional = when

    def __contains__(self, key):
        return key in self.values

    def get(self, key):
        return self.values.get(key)


# End of file #
