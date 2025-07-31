import ast
from typespy import *
from Inferencer import *

printer = ASTPrinter()

def test_code(code, hint=None):
    node = ast.parse(code)
    inferencer = Inferencer(hint)
    print(ast.dump(node))
    for stmt in node.body:
        # printer.visit(stmt)
        inferred_type = inferencer.infer(stmt)
        print(f"Inferred type of '{ast.unparse(stmt)}' is: {inferred_type}")


if __name__ == "__main__":
    code1 = """
def id(x): return x
"""
    code2 = """
def id(x): return x
y = id("ddf")
"""

    code3 = """
f = lambda x: x
g = f(5)
"""

    code4 = """
def add1(x): return x + 1
z = add1(10)
"""
    code5 = """
f = lambda z: z * 2
"""
    code6="""
new_dict = {
    "val1": 1,
    "val2": 2
}
"""

    code7 = """
my_config = {
    "key1": "dfd",
    "key2": 10
}
def get_config_value(key_name):
    return my_config.get(key_name)

value1 = get_config_value("key1")
"""
    code8 = """
my_config = {
    "key1": "dfd",
    "key2": 10
}
def get_config_value(key_name):
    return my_config[key_name]

value1 = get_config_value("key1")
"""

    hint = {"key1": TStr(), "key2": TInt()}  

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
    print("\nTest 7:")
    test_code(code7,hint)
    print("\nTest 8:")
    test_code(code8,hint)
