from enum import Enum


class DigramType(Enum):
    SIMPLE = 0
    LABEL = 1


class DigramLogic(Enum):
    SIMPLE = 0
    LABEL = 1
    MOST_USED = 2
    RANDOM = 3
    MOST_SAVE = 4
    # ToDo Add other logics. For example: Select digram for which it is calculated, that it saves more space
    # Another example: First all SIMPLE than only LABEL


class NodeType(Enum):
    NODE = 0
    RULE = 1
    PARAMETER = 2
    LABEL = 3
