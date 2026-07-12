from enum import IntEnum, unique


@unique
class Action(IntEnum):

    # From `evtest` output, the "magic numbers" for assignment
    # to enums:
    #   0 == 'released'
    #   1 == 'pressed'
    #   2 == 'repeated'

    RELEASE, PRESS, REPEAT = range(3)

    @property
    def is_pressed(self):
        return self == Action.PRESS or self == Action.REPEAT

    @property
    def just_pressed(self):
        return self == Action.PRESS

    @property
    def is_released(self):
        return self == Action.RELEASE

    @property
    def is_repeat(self):
        return self == Action.REPEAT

    def __str__(self):
        return self.name.lower()


PRESS                           = Action.PRESS
RELEASE                         = Action.RELEASE
REPEAT                          = Action.REPEAT
