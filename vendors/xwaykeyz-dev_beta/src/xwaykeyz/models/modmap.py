class Modmap:
    def __init__(self, name, mappings, when=None):
        self.name = name
        self.mappings = mappings
        self.conditional = when

    def __contains__(self, key):
        return key in self.mappings

    def __getitem__(self, item):
        return self.mappings[item]


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
