# Parallel External Integer Sort

This program sorts large integer files that may be bigger than available RAM.
It uses external merge sort: the input is split into memory-limited chunks, each chunk is sorted in parallel, and the sorted chunks are merged into one final sorted output file.

## Main Features

- Sorts large files without loading the whole file into memory.
- Uses all available CPU cores by default.
- Accepts a memory limit as the maximum number of integers loaded at one time.
- Creates the sorted output file in the same directory as the input file by default.
- Supports:
  - text files with one integer per line;
  - binary files containing continuous 32-bit integers without a header;
  - automatic format detection.

## Files

external_int32_sort.py   Main program
requirements.txt         Python dependency list
.gitignore               Git ignore rules
README.md                Project documentation

## Installation

bash
pip install -r requirements.txt

## Basic Usage

bash
python external_int32_sort.py <input_file> <memory_numbers>

`memory_numbers` is the maximum number of integers that may be loaded into memory at the same time.

Example:
bash
python external_int32_sort.py random_numbers.txt 12288

Default output:
text
random_numbers.sorted.txt

## Text File Usage

For a text file with one integer per line:
bash
python external_int32_sort.py random_numbers.txt 12288 --format text

Overwrite an existing output file:
bash
python external_int32_sort.py random_numbers.txt 12288 --format text --force

## Binary File Usage

For a binary file containing signed 32-bit integers:

bash
python external_int32_sort.py numbers.bin 1000000 --format binary --endian little

For unsigned 32-bit integers:

bash
python external_int32_sort.py numbers.bin 1000000 --format binary --unsigned

## Output Rule

If `--output` is not provided, the sorted file is created next to the input file:

<input_name>.sorted<extension>