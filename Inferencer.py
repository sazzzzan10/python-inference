import ast
from typespy import *
from utils import *
class Inferencer:
    def __init__(self,hint=None):
        self.env = TypeEnv()
        self.subst = {}
        self.hint=hint
        self.function_retrieves_from = {}
            # print(self.env)
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
        elif isinstance(node, ast.BinOp):  #breaks the binary operation into left and right part and calls infer recursively for both, with current env until the rudimentary type is returned(tvar, int, str ...)
            # print("bin opt inside", node.left, node.right, env)
            left = self.infer(node.left, env)
            right = self.infer(node.right, env)
            # print("binop after: ", left, right, self.subst )
            unify(left, TInt(), self.subst) 
            unify(right, TInt(), self.subst)
            # print("before binop return: ", left)
            return TInt()
        elif isinstance(node, ast.Lambda):
            # print("lambda inside")

            arg_name = node.args.args[0].arg
            arg_type = self.fresh_var()
            new_env = env.clone()
            new_env[arg_name] = arg_type
            body_type = self.infer(node.body, new_env)
            # print("checking self subst before applying: ",self.subst)
            return TFun(apply_subst(arg_type, self.subst), apply_subst(body_type, self.subst))
        elif isinstance(node, ast.Call):
            # Special case: dict.get(key)
            # print("dict obj fdgffg", ast.dump(node), env)

            if isinstance(node.func, ast.Attribute) and node.func.attr == "get": #this part visited for function definition which includes retrieving dictionary value using get(),
                dict_obj = node.func.value
                # print("dict obj ", ast.dump(node), env)
                dict_type = self.infer(dict_obj, env)
                # print("dict type: ", dict_type)
                if isinstance(dict_type, TDict):
                    key_type = self.infer(node.args[0], env)
                    unify(key_type, dict_type.key_type, self.subst)
                    dict_type=apply_subst(dict_type.value_type, self.subst)
                    return dict_type
                else:
                    raise Exception(f".get called on non-dictionary type: {dict_type}")

            func_type = self.infer(node.func, env)
            arg_type = self.infer(node.args[0], env)
            ret_type = self.fresh_var()
            # print("values after return: ", func_type, TFun(arg_type, ret_type), self.subst)
            unify(func_type, TFun(arg_type, ret_type), self.subst)
            # print("values after return unify: ", func_type, TFun(arg_type, ret_type), self.subst)

            if (isinstance(node.func, ast.Name) and #this part is visited on calling the function which returns dict 
                len(node.args) == 1 and 
                isinstance(node.args[0], ast.Str)):
                
                func_name = node.func.id
                if func_name in self.function_retrieves_from: #checking if function retrieve has value, it links the function to dict which is to be returned, then it should have been stored in env along with hint which stores the corresponding types for each keys
                    dict_name = self.function_retrieves_from[func_name]
                    # print("dict name from function retrieve", dict_name, self.function_retrieves_from,env)
                    if dict_name in env:
                        dict_type = env[dict_name]
                        if isinstance(dict_type, TDict) and dict_type.hint:
                            key = node.args[0].s
                            if key in dict_type.hint:
                                return dict_type.hint[key]
            return apply_subst(ret_type, self.subst)

        elif isinstance(node, ast.FunctionDef): #works for only one arg. First takes arg, generates fresh type for the arg and adds to env. Then calls infer recursively for the body part with new env context(details about arg). Retrieves type of arg as self.subst(env) and finally generates t0->t1
            # print("functiondef inside", ast.dump(node), len(node.body))
            if len(node.body) == 1 and isinstance(node.body[0], ast.Return): #this part checks the function definition for which the body might return values got from dictionary. It requires calling function using get to retrieve value from dictionary or accessing directly which uses subscript
                ret_expr = node.body[0].value
                if ret_expr is not None:
                    if (isinstance(ret_expr, ast.Call) and
                        isinstance(ret_expr.func, ast.Attribute) and
                        ret_expr.func.attr == "get" and
                        isinstance(ret_expr.func.value, ast.Name)):
                        # print("ret_exp, call attribute", ast.dump(node))

                        dict_name = ret_expr.func.value.id #gets id of element(Name, int ... here name of dict ) contained in body to be returned from function
                        self.function_retrieves_from[node.name] = dict_name #extracts name of current function
                        # print("dict name function retrieves from", dict_name, node.name)
                    elif isinstance(ret_expr, ast.Subscript):
                        # print("dict obj d", ast.dump(ret_expr), ret_expr.value.id, node.name)
                        dict_name = ret_expr.value.id #extracts name of element, here dict
                        self.function_retrieves_from[node.name] = dict_name 
                        # print("dict name function retrieves from for subscript", dict_name, node.name)

            # print("ast for def function: ", ast.dump(node))   
            #extract argument and create fresh type for argument and store in environment        
            arg_name = node.args.args[0].arg
            arg_type = self.fresh_var()
            new_env = env.clone()
            new_env[arg_name] = arg_type
            #infer type for body using new env after argument work
            body_type = self.infer(node.body[0].value, new_env)  

            # print("inferring ",arg_type, self.subst, body_type)
            func_type = TFun(apply_subst(arg_type, self.subst), apply_subst(body_type, self.subst))
            env[node.name] = func_type
            # print("replacing env before call",func_type, node.name, env)
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
            # print("before inference dict: ", env)
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
                    # print("make values ",t,self.subst)
                    t_applied = apply_subst(t, self.subst)
                    # print("subst",t_applied,self.subst)
                    if not any(t_applied == u for u in unique): #save only unique, similar to not t_applied in set(unique)
                        unique.append(t_applied)
                if len(unique) == 1:
                    return unique[0]
                else:
                    return TUnion(unique)

            value_type = make_union(value_types)
            # print("after inference dict: ",self.subst, env, value_type)
            return TDict(apply_subst(key_type, self.subst), value_type, self.hint)
        elif isinstance(node, ast.Subscript):
            dict_obj = node.value # extract ast of type contained in subscript, here dict(my_config)
            # print("dict obj subscript ", ast.dump(node), env)
            dict_type = self.infer(dict_obj, env)
            # print("dict type: ", dict_type, self.subst)
            if isinstance(dict_type, TDict):
                key_type = self.infer(node.slice, env) #infers type for argument/slice sent 
                unify(key_type, dict_type.key_type, self.subst) #unifying the dict key type and argument(key) for my_config dict
                # print("after subscript key typing", key_type, dict_type.key_type, dict_type.value_type, self.subst)
                new_apply = apply_subst(dict_type.value_type, self.subst)
                # print("returning type of dict ", new_apply)
                return new_apply
                #  return apply_subst(dict_type.value_type, self.subst)
            else:
                raise Exception(f".get called on non-dictionary type: {dict_type}")
        else:
            raise Exception(f"Unknown AST node: {ast.dump(node)}")
