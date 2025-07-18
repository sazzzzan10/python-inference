# python-inference
This Python program implements a basic type inference engine using the Hindley-Milner algorithm to analyze simple Python code. It parses code into an abstract syntax tree (AST) and infers types for constructs like lambda expressions, single-parameter functions, function calls, variable assignments, and dictionary access. The `Inferencer` class handles the type logic through unification and substitution, while the `test_code()` function processes and prints inferred types for each test case. The `__main__` section runs several examples, demonstrating inference on identity functions, arithmetic, lambdas, and dictionary lookups, with optional hints to guide the process. Currently, it only infers basic types like int, str, bool and dict.
To test the program just run:
```
python main.py
```
An example output is shown below:
```
Inferred type of 'def add1(x):
    return x + 1' is: (int -> int)
Inferred type of 'z = add1(10)' is: int
```