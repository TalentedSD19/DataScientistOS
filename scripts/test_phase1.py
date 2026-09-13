from backend.workspace import create_workspace
from backend.docker_runner import exec_shell, run_python_file, destroy

create_workspace("demo")

# Write a tiny script from inside the container
exec_shell("demo", "echo 'print(1 + 1)' > src/main.py")

# Run it
print(run_python_file("demo", "src/main.py"))

# Prove the sandbox has pandas
print(exec_shell("demo", "python -c \"import pandas; print(pandas.__version__)\""))

destroy("demo")