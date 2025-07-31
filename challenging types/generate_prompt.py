import os
import sys

def find_python_files(root_dir):
    """Recursively yield all .py files under the given root directory."""
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith(".py"):
                yield os.path.join(dirpath, file)

def load_template(template_path):
    """Load the template from file."""
    with open(template_path, 'r') as f:
        return f.read()

def generate_task_file(source_path, template, output_dir):
    """Generate a single task file from a source Python file."""
    with open(source_path, 'r') as f:
        source_code = f.read().rstrip()

    placeholder = "{Contents to be added from a python file}"
    if placeholder not in template:
        raise ValueError("Placeholder not found in template.")

    result = template.replace(placeholder, source_code)

    # Get filename without path
    filename = os.path.basename(source_path)
    pathname = os.path.abspath(source_path)
    # print("Pathname ", pathname, filename)
    new_dir = pathname.replace("repo_without_types", "original_repo")
    name, _ = os.path.splitext(filename)
    output_filename = f"{name}.txt"
    new_comp_path = new_dir.replace(filename,output_filename)
    new_complete_path = new_dir.replace(filename,output_filename)
    # output_path = os.path.join(new_complete_path, output_filename)
    # print("new complete path: ", new_complete_path, output_path)
    try:
        with open(new_comp_path, 'w') as f:
            f.write(result)
    except Exception as e:
        print(e)
    print(f"✅ Generated: {new_dir}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_task_files.py <root_directory>")
        sys.exit(1)

    root_dir = sys.argv[1]
    template_path = "task_template.txt"
    output_dir = "output"

    if not os.path.exists(template_path):
        print(f"Error: Template file '{template_path}' not found.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    template = load_template(template_path)

    py_files = list(find_python_files(root_dir))
    # print("python files: ", py_files)
    if not py_files:
        print("No Python files found.")
        sys.exit(0)
    number_file = 0
    for py_file in py_files:
        generate_task_file(py_file, template, output_dir)
        number_file = number_file + 1
    print("Total number of files: ", number_file)

if __name__ == "__main__":
    main()
