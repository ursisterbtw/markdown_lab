import os

def lint_and_uncapitalize_comments(file_path):
    """
    Lint a file for comments with leading capital letters and uncapitalize them.
    Modify the file in place.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        modified_lines = []
        for line in lines:
            stripped_line = line.lstrip()
            if stripped_line.startswith("#"):
                # find the comment text after the `#`
                comment = stripped_line[1:].lstrip()
                # check if it starts with a capital letter
                if comment and comment[0].isupper():
                    # replace the line with the uncapitalized comment
                    new_comment = comment[0].lower() + comment[1:]
                    line = line.replace(comment, new_comment, 1)
            modified_lines.append(line)

        # write the changes back to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(modified_lines)

        print(f"Processed: {file_path}")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_directory(directory_path):
    """
    Process all Python files in a directory, linting comments for leading capital letters.
    """
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith('.py'):  # Only process Python files
                file_path = os.path.join(root, file_name)
                lint_and_uncapitalize_comments(file_path)

if __name__ == "__main__":
    dir_path = input("Enter the directory path to process: ").strip()
    if os.path.exists(dir_path):
        process_directory(dir_path)
    else:
        print("Invalid directory path.")
