import itertools

class Type:
    def __str__(self):
        return self.pretty()

    def pretty(self):
        raise NotImplementedError


class TVar(Type):
    _id_iter = itertools.count()

    def __init__(self, name=None):
        # print(TVar._id_iter)
        self.id = next(TVar._id_iter)
        self.name = name or f't{self.id}'

    def pretty(self):
        return self.name

class TFun(Type):
    def __init__(self, arg_type, ret_type):
        self.arg = arg_type
        self.ret = ret_type

    def pretty(self):
        return f"({self.arg.pretty()} -> {self.ret.pretty()})"

class TInt(Type):
    def pretty(self):
        return "int"

class TBool(Type):
    def pretty(self):
        return "bool"

class TStr(Type):
    def pretty(self):
        return "str"


class TypeEnv(dict):
    def clone(self):
        return TypeEnv(self)

class TDict(Type):
    def __init__(self, key_type, value_type, hint=None):
        self.key_type = key_type
        self.value_type = value_type
        self.hint = hint

    def pretty(self):
        return f"Dict[{self.key_type.pretty()}, {self.value_type.pretty()}]"


class TUnion(Type):
    def __init__(self, options): 
        self.options = options
    def pretty(self): 
        return " | ".join(t.pretty() for t in self.options)
    # def pretty(self):
    #     new_set=set(map(str,self.types))
    #     if len(new_set) > 1:
    #         return " | ".join(map(str, self.types))
    #     else:
    #         return self.types[0]
    def __eq__(self, other):
        return isinstance(other, TUnion) and set(self.types) == set(other.types)

