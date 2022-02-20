
def get_requirements():
    return __get_py_modules("requirements.txt")


def get_dev_requirements():
    return __get_py_modules("dev-requirements.txt")


def __get_py_modules(filepath: str):
    with open(filepath, "r") as file:
        modules = []
        for line in file.readlines():
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith("#"):
                continue
            modules.append(stripped_line)
        return modules
