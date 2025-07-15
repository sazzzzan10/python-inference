import ast
import itertools
from collections import namedtuple


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
    def __init__(self, key_type, value_type):
        self.key_type = key_type
        self.value_type = value_type

    def pretty(self):
        return f"Dict[{self.key_type.pretty()}, {self.value_type.pretty()}]"


class TUnion(Type):
    def __init__(self, types):
        self.types = types
    def pretty(self):
        return " | ".join(map(str, self.types))
    def __eq__(self, other):
        return isinstance(other, TUnion) and set(self.types) == set(other.types)



def occurs_check(v: TVar, typ: Type, subst: dict):
    typ = apply_subst(typ, subst)
    # print("after check apply subst: ",typ, v, typ, subst)
    if typ == v:
        return True
    elif isinstance(typ, TFun):
        return occurs_check(v, typ.arg, subst) or occurs_check(v, typ.ret, subst)
    return False

def unify(t1: Type, t2: Type, subst: dict):
    # print("before unify: ",t1, t2)
    t1 = apply_subst(t1, subst)
    t2 = apply_subst(t2, subst)
    # print("after unify: ",t1, t2)

    if isinstance(t1, TVar):
        if t1 != t2:
            if occurs_check(t1, t2, subst):
                raise Exception("Recursive unification")
            subst[t1] = t2
            # print("substitute created: ",subst)
    elif isinstance(t2, TVar):
        # print("inside second instance")
        unify(t2, t1, subst)
    elif isinstance(t1, TFun) and isinstance(t2, TFun):
        unify(t1.arg, t2.arg, subst)
        unify(t1.ret, t2.ret, subst)
    elif type(t1) != type(t2):
        raise Exception(f"Type mismatch: {t1.pretty()} vs {t2.pretty()}")

def apply_subst(t: Type, subst: dict):
    # print("apply sub: ", t, subst)
    if isinstance(t, TVar):
        replacement = subst.get(t, t)
        if replacement == t:
            return t
        return apply_subst(replacement, subst)
    elif isinstance(t, TFun):
        return TFun(apply_subst(t.arg, subst), apply_subst(t.ret, subst))
    elif isinstance(t, TDict):
        return TDict(apply_subst(t.key_type, subst), apply_subst(t.value_type, subst))
    elif isinstance(t, TUnion):
        return TUnion([apply_subst(t, subst) for t in t.types])
    return t


# === Type Inference ===

class Inferencer:
    def __init__(self):
        self.env = TypeEnv()
        self.subst = {}

    def fresh_var(self):
        return TVar()

    def infer(self, node, env=None):
        if env is None:
            env = self.env

        if isinstance(node, ast.Num):
            return TInt()
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, int):
                return TInt()
            elif isinstance(node.value, bool):
                return TBool()
            elif isinstance(node.value, str):
                return TStr()
            else:
                raise Exception("Unknown literal type")
        elif isinstance(node, ast.Name):
            if node.id in env:
                # print("env name: ", node.id, env)
                return env[node.id]
            else:
                raise Exception(f"Unbound variable {node.id}")
        elif isinstance(node, ast.BinOp):
            left = self.infer(node.left, env)
            right = self.infer(node.right, env)
            # print("binop: ", left, right )
            unify(left, TInt(), self.subst) 
            unify(right, TInt(), self.subst)
            return TInt()
        elif isinstance(node, ast.Lambda):
            arg_name = node.args.args[0].arg
            arg_type = self.fresh_var()
            new_env = env.clone()
            new_env[arg_name] = arg_type
            body_type = self.infer(node.body, new_env)
            # print("checking self subst before applying: ",self.subst)
            return TFun(apply_subst(arg_type, self.subst), apply_subst(body_type, self.subst))
        elif isinstance(node, ast.Call):
            func_type = self.infer(node.func, env)
            arg_type = self.infer(node.args[0], env)
            ret_type = self.fresh_var()
            unify(func_type, TFun(arg_type, ret_type), self.subst)
            return apply_subst(ret_type, self.subst)
        elif isinstance(node, ast.FunctionDef):
            arg_name = node.args.args[0].arg
            arg_type = self.fresh_var()
            new_env = env.clone()
            new_env[arg_name] = arg_type
            body_type = self.infer(node.body[0].value, new_env)  
            func_type = TFun(apply_subst(arg_type, self.subst), apply_subst(body_type, self.subst))
            env[node.name] = func_type
            return func_type
        elif isinstance(node, ast.Assign):
            assert len(node.targets) == 1, "Only single assignments supported"
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                raise Exception("Only simple name assignments supported")
            value_type = self.infer(node.value, env)
            env[target.id] = value_type
            return value_type
        elif isinstance(node, ast.Dict):
            key_types = []
            value_types = []
            for k, v in zip(node.keys, node.values):
                kt = self.infer(k, env)
                vt = self.infer(v, env)
                key_types.append(kt)
                value_types.append(vt)

            # unify all key types (assuming same key type, e.g., str)
            key_type = key_types[0]
            for kt in key_types[1:]:
                unify(kt, key_type, self.subst)

            # compute union of value types
            def make_union(types):
                unique = []
                for t in types:
                    t_applied = apply_subst(t, self.subst)
                    if not any(t_applied == u for u in unique):
                        unique.append(t_applied)
                if len(unique) == 1:
                    return unique[0]
                else:
                    return TUnion(unique)

            value_type = make_union(value_types)
            return TDict(apply_subst(key_type, self.subst), value_type)

        else:
            raise Exception(f"Unknown AST node: {ast.dump(node)}")

# === Testing ===

def test_code(code):
    node = ast.parse(code)
    inferencer = Inferencer()
    for stmt in node.body:
        inferred_type = inferencer.infer(stmt)
        print(f"Inferred type of '{ast.unparse(stmt)}' is: {inferred_type}")

# === Example Programs ===

if __name__ == "__main__":
    # Identity function
    code1 = """
def id(x): return x
"""
    # Function application
    code2 = """
def id(x): return x
y = id("ddf")
"""

    # Lambda
    code3 = """
f = lambda x: x
g = f(5)
"""

    # Arithmetic
    code4 = """
def add1(x): return x + 1
z = add1(10)
"""
    code5 = """
f = lambda z: z * 2
"""
    code6 = """
my_config = {
    "timeout": "dfd",
    "retries": 10
}

"""

    print("Test 1:")
    test_code(code1)
    print("\nTest 2:")
    test_code(code2)
    print("\nTest 3:")
    test_code(code3)
    print("\nTest 4:")
    test_code(code4)
    print("\nTest 5:")
    test_code(code5)
    print("\nTest 6:")
    test_code(code6)