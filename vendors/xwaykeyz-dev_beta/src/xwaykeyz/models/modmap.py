# src/xwaykeyz/models/modmap.py

from ..lib.conditional_guard import call_conditional


class Modmap:
    def __init__(self, name, mappings, when=None):
        self.name = name
        self.mappings = mappings
        self.conditional = when

    def __contains__(self, key):
        return key in self.mappings

    def __getitem__(self, item):
        return self.mappings[item]

    def matches(self, ctx):
        return call_conditional('modmap', self.name, self.conditional, ctx)


class MultiModmap:
    def __init__(self, name, mappings, when=None):
        self.name = name
        self.mappings = mappings
        self.conditional = when

    def __contains__(self, key):
        return key in self.mappings

    def __getitem__(self, item):
        return self.mappings[item]

    def items(self):
        return self.mappings.items()

    def matches(self, ctx):
        return call_conditional('multipurpose_modmap', self.name, self.conditional, ctx)


# End of file #
