# Parallel External Text Integer Sort

This project contains a Python program for sorting large text files that contain one integer per line.

The program is designed for files that may be too large to load into memory at once. It splits the input into smaller parts, sorts those parts in parallel, and then merges the sorted parts into one final sorted file.

## Main Functionality

- Sorts text files containing integers.
- Expects one integer per line.
- Does not require a file header.
- Processes the file in memory-limited chunks.
- Uses multiple CPU cores for chunk sorting and merging.
- Creates the output file in the same directory as the input file by default.

## Input Requirements

The input file must be a text file with this structure:

```text
2376839878
2609102346
593120616
1346096396
Important requirements:

Each non-empty line must contain one integer.
Empty lines are ignored.
The file must not contain a header row.
The file should be encoded as UTF-8 text.
Project Files
external_int32_sort.py    Main sorting program
requirements.txt          Python dependency file
README.md                 Project description and usage guide
.gitignore                Git ignore rules
Installation
The current text-only version uses only the Python standard library.

If you still keep requirements.txt, you may install it with:

pip install -r requirements.txt
Usage
Run the program from the project directory:

python external_int32_sort.py <input_file> <memory_numbers>
Example:

python external_int32_sort.py random_numbers.txt 12288
memory_numbers means the maximum number of integers that may be loaded into memory at the same time.

Output File
If --output is not provided, the program creates the sorted file next to the input file.

For this input:

random_numbers.txt
The default output is:

random_numbers.sorted.txt
Useful Options
Specify a custom output file:

python external_int32_sort.py random_numbers.txt 12288 --output result.txt
Overwrite an existing output file:

python external_int32_sort.py random_numbers.txt 12288 --force
Set the number of worker processes:

python external_int32_sort.py random_numbers.txt 12288 --workers 4
VS Code Debug Arguments
If you run the program through VS Code Debugger, pass arguments in .vscode/launch.json:

"args": [
  "random_numbers.txt",
  "12288",
  "--force"
]
Do not pass --format text, because the current program version only supports text input and no longer defines a --format option.