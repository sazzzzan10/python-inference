from typespy import *
import ast

class ASTPrinter(ast.NodeVisitor):
    def visit(self, node):
        print(f"{type(node).__name__}: {ast.dump(node, annotate_fields=True)}")
        self.generic_visit(node)

def occurs_check(v: TVar, typ: Type, subst: dict):
    typ = apply_subst(typ, subst)
    # print("after check apply subst: ",typ, v, typ, subst)
    if typ == v:
        return True
    elif isinstance(typ, TFun):
        return occurs_check(v, typ.arg, subst) or occurs_check(v, typ.ret, subst)
    return False

'''
unify(t1, t2, subst): Modifies subst to make t1 and t2 equal types (if possible). Adds new info to subst.
unify(TVar('a'), TInt(), subst)
subst = { TVar('a'): TInt() }
'''

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
            # print("substitute created: ",t1,subst)
    elif isinstance(t2, TVar):
        unify(t2, t1, subst)
    elif isinstance(t1, TFun) and isinstance(t2, TFun):
        unify(t1.arg, t2.arg, subst)
        unify(t1.ret, t2.ret, subst)
    elif type(t1) != type(t2):
        raise Exception(f"Type mismatch: {t1.pretty()} vs {t2.pretty()}")


'''
If the type is a variable (TVar) and has a substitution, recursively looks up in subst for its final replacement.

If the type is a function type (TFun), applies substitution to both its argument and return types after looking in subst.
subst = { 'a': TInt() }
t = TFun(TVar('a'), TVar('a'))
apply_subst(t, subst)
→ TFun(TInt(), TInt())
'''

def apply_subst(t: Type, subst: dict):

    if isinstance(t, TVar):
        # print("checking instance",t)
        replacement = subst.get(t, t)
        if replacement == t:
            return t
        return apply_subst(replacement, subst)
    elif isinstance(t, TFun):
        return TFun(apply_subst(t.arg, subst), apply_subst(t.ret, subst))
    return t
