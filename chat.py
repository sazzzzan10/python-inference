import ast
import itertools
from collections import namedtuple

class ASTPrinter(ast.NodeVisitor):
    def visit(self, node):
        print(f"{type(node).__name__}: {ast.dump(node, annotate_fields=True)}")
        self.generic_visit(node)
 
class Type:
    def __str__(self):
        return self.pretty()

    def pretty(self):
        raise NotImplementedError

class TVar(Type):
    _id_iter = itertools.count()

    def __init__(self, name=None):
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
    def __init__(self, options): self.options = options
    def pretty(self): return " | ".join(t.pretty() for t in self.options)

class TNone(Type):
    def pretty(self): return "None"

class TExactDict(Type):
    def __init__(self, mapping: dict[str, Type]):
        self.mapping = mapping

    def pretty(self):
        items = ", ".join(f"{k}: {v.pretty()}" for k, v in self.mapping.items())
        return f"{{{items}}}"

    def __eq__(self, other):
        return isinstance(other, TExactDict) and self.mapping == other.mapping
    
def occurs_check(v: TVar, typ: Type, subst: dict):
    typ = apply_subst(typ, subst)
    if typ == v:
        return True
    elif isinstance(typ, TFun):
        return occurs_check(v, typ.arg, subst) or occurs_check(v, typ.ret, subst)
    return False

def unify(t1: Type, t2: Type, subst: dict):
    t1 = apply_subst(t1, subst)
    t2 = apply_subst(t2, subst)

    if isinstance(t1, TVar):
        if t1 != t2:
            if occurs_check(t1, t2, subst):
                raise Exception("Recursive unification")
            subst[t1] = t2
    elif isinstance(t2, TVar):
        unify(t2, t1, subst)
    elif isinstance(t1, TFun) and isinstance(t2, TFun):
        unify(t1.arg, t2.arg, subst)
        unify(t1.ret, t2.ret, subst)
    elif type(t1) != type(t2):
        raise Exception(f"Type mismatch: {t1.pretty()} vs {t2.pretty()}")

def apply_subst(t: Type, subst: dict):
    if isinstance(t, TVar):
        replacement = subst.get(t, t)
        if replacement == t:
            return t
        return apply_subst(replacement, subst)
    elif isinstance(t, TFun):
        return TFun(apply_subst(t.arg, subst), apply_subst(t.ret, subst))
    return t

def parse_annotation(node: ast.expr) -> Type:
    if isinstance(node, ast.Name):
        if node.id == 'int': return TInt()
        if node.id == 'str': return TStr()
        if node.id == 'bool': return TBool()
        if node.id == 'None': return TNone()
    elif isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name):
            name = node.value.id
            if name == 'dict' or name == 'Dict':
                key_type = parse_annotation(node.slice.elts[0])
                val_type = parse_annotation(node.slice.elts[1])
                return TDict(key_type, val_type)
            if name == 'list' or name == 'List':
                return TList(parse_annotation(node.slice))
            if name == 'Union':
                return TUnion([parse_annotation(e) for e in node.slice.elts])
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # e.g. int | str
        return TUnion([parse_annotation(node.left), parse_annotation(node.right)])
    raise Exception(f"Unknown annotation: {ast.dump(node)}")


# === Type Inference ===

class Inferencer:
    def __init__(self,hints=None):
        self.env = TypeEnv()
        self.subst = {}
        if hints:
            self.env.update(hints)
    def fresh_var(self):
        return TVar()
    def types_equal(self, t1, t2):
        return apply_subst(t1, self.subst) == apply_subst(t2, self.subst)

    def infer(self, node, env=None):
        if env is None:
            env = self.env
            print(env)
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
                return env[node.id]
            else:
                raise Exception(f"Unbound variable {node.id}")
        elif isinstance(node, ast.Expr):
            return self.infer(node.value, env)

        elif isinstance(node, ast.Module):
            result = None
            for stmt in node.body:
                result = self.infer(stmt, env)
            return result
        elif isinstance(node, ast.BinOp):
            left = self.infer(node.left, env)
            right = self.infer(node.right, env)
            unify(left, TInt(), self.subst) 
            unify(right, TInt(), self.subst)
            return TInt()
        elif isinstance(node, ast.Lambda):
            arg_name = node.args.args[0].arg
            arg_type = self.fresh_var()
            new_env = env.clone()
            new_env[arg_name] = arg_type
            body_type = self.infer(node.body, new_env)
            return TFun(apply_subst(arg_type, self.subst), apply_subst(body_type, self.subst))
        elif isinstance(node, ast.Call):
            func_type = self.infer(node.func, env)
            arg_type = self.infer(node.args[0], env)
            ret_type = self.fresh_var()
            unify(func_type, TFun(arg_type, ret_type), self.subst)
            return apply_subst(ret_type, self.subst)

        elif isinstance(node, ast.FunctionDef):
            arg_name = node.args.args[0].arg
            # arg_type = self.fresh_var()
            arg_node = node.args.args[0]
            if arg_node.annotation:
                arg_type = parse_annotation(arg_node.annotation)
            else:
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
            env[target.id] = apply_subst(value_type, self.subst)            
            return value_type
        elif isinstance(node, ast.Dict):
            keys = [self.infer(k, env) for k in node.keys]
            vals = [self.infer(v, env) for v in node.values]

            # Unify all keys into one key type
            key_type = keys[0]
            for k in keys[1:]:
                unify(key_type, k, self.subst)

            # Combine distinct value types into a union
            unique_val_types = []
            for v in vals:
                if all(not self.types_equal(v, u) for u in unique_val_types):
                    unique_val_types.append(v)

            val_type = (
                unique_val_types[0]
                if len(unique_val_types) == 1
                else TUnion(unique_val_types)
            )

            return TDict(key_type, val_type)
        elif isinstance(node, ast.Attribute):
            # We are analyzing an expression like `config.get`
            val_type = self.infer(node.value, env)
            attr = node.attr

            if isinstance(val_type, TDict) and attr == "get":
                return TFun(val_type.key_type, TUnion([val_type.value_type, TNone()]))

            raise Exception(f"Unhandled attribute access: {attr} on {val_type}")
        else:
            raise Exception(f"Unknown AST node: {ast.dump(node)}")


source = """
my_config = {
    "timeout": "dfd",
    "retries": 10
}
def get_config_value(key_name):
    return my_config.get(key_name)

value1 = get_config_value("timeout")
"""

hints = {
    'my_config': TExactDict({
        "timeout": TStr(),
        "retries": TInt()
    }),
    # 'get_config_value': TFun(TStr(), TStr())  # Optional override
}


def test_code(code: str, hints=None):
    tree = ast.parse(code)
    inferencer = Inferencer(hints=hints)

    for stmt in tree.body:
        try:
            inferred_type = inferencer.infer(stmt)
            print(f"Inferred type of '{ast.unparse(stmt)}' is: {inferred_type}")
        except Exception as e:
            print(f"{ast.unparse(stmt)}  ⇒  ❌ {e}")

test_code(source)