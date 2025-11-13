import os

def write_tree_and_py_content(root_dir, output_file):
    TARGET_FOLDERS = {"app", "static"}
    TARGET_EXTENSIONS = {".py", ".js", ".html"}

    with open(output_file, "w", encoding="utf-8") as f:
        def walk(dir_path, prefix=""):
            items = sorted(os.listdir(dir_path))
            for i, item in enumerate(items):
                # Пропускаем папку venv на любом уровне
                if item == "venv":
                    continue

                path = os.path.join(dir_path, item)
                connector = "└── " if i == len(items) - 1 else "├── "
                f.write(prefix + connector + item + "\n")

                if os.path.isdir(path):
                    extension = "    " if i == len(items) - 1 else "│   "
                    walk(path, prefix + extension)

        # 1️⃣ Записываем дерево проекта
        f.write(f"{os.path.basename(root_dir)}\n")
        walk(root_dir)

        # 2️⃣ Контент только из app и static
        f.write("\n\n# Files content (only from 'app' and 'static' folders)\n\n")

        for dirpath, _, filenames in os.walk(root_dir):
            # Полностью игнорируем пути, где встречается venv
            if "venv" in dirpath.split(os.sep):
                continue

            # Проверяем, что путь содержит одну из целевых папок
            if not any(folder in dirpath.split(os.sep) for folder in TARGET_FOLDERS):
                continue

            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                if ext in TARGET_EXTENSIONS:
                    filepath = os.path.join(dirpath, filename)
                    relpath = os.path.relpath(filepath, root_dir)
                    f.write(f"\n--- {relpath} ---\n")
                    try:
                        with open(filepath, "r", encoding="utf-8") as file:
                            f.write(file.read())
                    except Exception as e:
                        f.write(f"\n[Ошибка чтения файла: {e}]\n")

if __name__ == "__main__":
    current_dir = os.getcwd()
    write_tree_and_py_content(current_dir, "project_structure.txt")
    print("Готово! Смотри файл project_structure.txt")
