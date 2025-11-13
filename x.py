import os

def write_tree_and_file_contents(root_dir, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        def walk(dir_path, prefix=""):
            items = sorted(os.listdir(dir_path))
            for i, item in enumerate(items):
                path = os.path.join(dir_path, item)

                if item in {".venv", "__pycache__"} or item.startswith("."):
                    continue

                connector = "└── " if i == len(items) - 1 else "├── "
                f.write(prefix + connector + item + "\n")
                if os.path.isdir(path):
                    extension = "    " if i == len(items) - 1 else "│   "
                    walk(path, prefix + extension)

        f.write(f"{os.path.basename(root_dir)}\n")
        walk(root_dir)

        f.write("\n\n# Содержимое Python, JavaScript, HTML и .env файлов\n\n")

        count = 0
        for dirpath, _, filenames in os.walk(root_dir):
            if ".venv" in dirpath.split(os.sep) or "__pycache__" in dirpath:
                continue

            for filename in filenames:
                if filename.endswith((".py", ".js", ".html", ".env")):
                    filepath = os.path.join(dirpath, filename)
                    relpath = os.path.relpath(filepath, root_dir)
                    f.write(f"\n--- {relpath} ---\n")
                    try:
                        with open(filepath, "r", encoding="utf-8") as source_file:
                            f.write(source_file.read())
                            count += 1
                    except Exception as e:
                        f.write(f"\n[Ошибка чтения файла: {e}]\n")

        f.write(f"\n\n# Всего файлов записано: {count}\n")

if __name__ == "__main__":
    current_dir = os.getcwd()
    write_tree_and_file_contents(current_dir, "project_structure.txt")
    print("✅ Готово! Смотри файл project_structure.txt")
