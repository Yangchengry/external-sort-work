from __future__ import annotations #optional一个附加功能，能使整个程序在运行时暂时将类型标注存为字符，并在下文中需要的地方调用，从而避免产生程序错误

import argparse
import heapq #用这个函数库能实现找到当前文件最小数的功能
import multiprocessing as mp #多cpu核心同时操作
import os
import tempfile
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, as_completed, wait
from pathlib import Path


INT_BYTES = 4
TEXT_WRITE_BATCH_SIZE = 8192


def default_output_path(source: Path) -> Path: #在新文件中生成结果对应文件名
    return source.with_name(f"{source.stem}.sorted{source.suffix}")


def write_text_values(output, values: list[int]) -> None: #把整数写进txt文件
    lines: list[str] = []
    for value in values:
        lines.append(f"{value}\n") #数字转成字符串
        if len(lines) >= TEXT_WRITE_BATCH_SIZE:
            output.write("".join(lines))
            lines.clear()

    if lines:
        output.write("".join(lines))


def scan_text_ranges(input_path: Path, numbers_per_chunk: int) -> list[tuple[int, int]]:#文本文件分块
    ranges: list[tuple[int, int]] = []#返回一个列表

    with open(input_path, "rb") as src:#rb是用二进制方式读取文件
        start = src.tell()
        count = 0

        while True:
            line = src.readline()#循环读取,一次读取一行
            if not line:
                end = src.tell()
                if count:
                    ranges.append((start, end))
                break

            if line.strip():
                count += 1

            if count == numbers_per_chunk:
                end = src.tell()
                ranges.append((start, end))
                start = end
                count = 0
                #小块满了就停止并记录范围(start,end)
    return ranges


def sort_text_range(input_path: str, start_byte: int, end_byte: int, output_path: str) -> str:
    values: list[int] = []

    with open(input_path, "rb") as src:
        src.seek(start_byte)
        while src.tell() < end_byte:
            line = src.readline()
            if not line:
                break
            stripped = line.strip()
            if stripped:
                text = stripped.decode("utf-8-sig" if start_byte == 0 and not values else "utf-8")
                values.append(int(text))

    values.sort()#给当前分块排序
    with open(output_path, "w", encoding="utf-8", newline="\n") as out:
        write_text_values(out, values)#排好序的分块内容整成临时文件

    return output_path


def read_next_int(file_obj):#读下一个整数
    line = file_obj.readline()
    while line and not line.strip():
        line = file_obj.readline()
    return int(line) if line else None


def merge_text_runs(input_paths: list[str], output_path: str) -> str:#把排好序的临时文件合成大文件
    files = [open(path, "r", encoding="utf-8") for path in input_paths]
    heap = []

    try:
        for index, file_obj in enumerate(files):
            value = read_next_int(file_obj)
            if value is not None:
                heapq.heappush(heap, (value, index))#把每个临时文件的第一个数字放进同一个堆

        with open(output_path, "w", encoding="utf-8", newline="\n") as out:
            output_buffer: list[int] = []
            while heap:
                value, index = heapq.heappop(heap)#堆里还有数就不停取出堆中当前最小值
                output_buffer.append(value)#放进缓冲区
                if len(output_buffer) >= TEXT_WRITE_BATCH_SIZE:
                    write_text_values(out, output_buffer)
                    output_buffer.clear()

                next_value = read_next_int(files[index])
                if next_value is not None:
                    heapq.heappush(heap, (next_value, index))

            write_text_values(out, output_buffer)
    finally:
        for file_obj in files:
            file_obj.close()

    return output_path


def make_initial_text_runs(
    input_path: Path,
    temp_dir: Path,
    memory_numbers: int,
    workers: int,
) -> list[Path]:#开始生成多个任务块，并同时独立进行每块中对应临时文件的排序
    active_workers = min(workers, memory_numbers)
    chunk_numbers = max(1, memory_numbers // active_workers)#限制处理进程大小，避免超过内存限制
    ranges = scan_text_ranges(input_path, chunk_numbers)#将大文件分块
    if not ranges:
        return []

    runs: list[Path] = []
    active_workers = min(workers, len(ranges), memory_numbers)
    with ProcessPoolExecutor(max_workers=active_workers) as executor:#多进程
        pending = set()
        range_iter = iter(enumerate(ranges))

        while True:
            while len(pending) < active_workers:
                try:
                    index, (start_byte, end_byte) = next(range_iter)
                except StopIteration:
                    break
                run_path = temp_dir / f"run_000000_{index:08d}.txt"
                pending.add(
                    executor.submit(
                        sort_text_range,
                        str(input_path),
                        start_byte,
                        end_byte,
                        str(run_path),
                    )
                )

            if not pending:
                break

            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                runs.append(Path(future.result()))

    return sorted(runs)


def merge_all_text_runs(
    runs: list[Path],
    temp_dir: Path,
    memory_numbers: int,
    workers: int,
) -> Path:#合并所有分好的临时文本块
    pass_index = 1
    current_runs = runs

    while len(current_runs) > 1:
        active_merges = min(workers, max(1, len(current_runs) // 2), max(1, memory_numbers // 3))
        memory_per_merge = max(3, memory_numbers // active_merges)
        fan_in = min(64, max(2, memory_per_merge - 1), len(current_runs))#max number of each mission's files to be combined

        groups = [
            current_runs[index : index + fan_in]
            for index in range(0, len(current_runs), fan_in)
        ]#make groups for every selecting mission

        next_runs: list[Path] = []
        with ProcessPoolExecutor(max_workers=active_merges) as executor:
            future_to_group = {}
            for group_index, group in enumerate(groups):
                out_path = temp_dir / f"run_{pass_index:06d}_{group_index:08d}.txt"
                future = executor.submit(merge_text_runs, [str(path) for path in group], str(out_path))#submit combining mission
                future_to_group[future] = group

            for future in as_completed(future_to_group):
                out_path = Path(future.result())
                next_runs.append(out_path)
                for old_path in future_to_group[future]:
                    old_path.unlink(missing_ok=True)#delete partial files that have already been combined

        current_runs = sorted(next_runs)
        pass_index += 1

    return current_runs[0]


def external_text_sort(
    input_path: Path,
    output_path: Path,
    memory_numbers: int,
    workers: int,
    force: bool,
) -> None:#this section combines all the functions above
    if memory_numbers < 3:#check memory size,too small can not operate properly
        raise ValueError("memory_numbers must be at least 3")

    if output_path.exists() and not force:
        raise FileExistsError(f"output file already exists: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)#make sure the path of the output exist
    workers = max(1, min(workers, os.cpu_count() or 1, memory_numbers))#limit number of workers as cpu numbers

    with tempfile.TemporaryDirectory(prefix=f"{input_path.stem}_sort_", dir=input_path.parent) as tmp:#temporary dictionary for storing sorted partial files
        temp_dir = Path(tmp)
        runs = make_initial_text_runs(input_path, temp_dir, memory_numbers, workers)
        if not runs:
            output_path.write_text("", encoding="utf-8")
            return

        final_run = merge_all_text_runs(runs, temp_dir, memory_numbers, workers)

        os.replace(final_run, output_path)


def parse_args() -> argparse.Namespace:#define how users could make the program work
    parser = argparse.ArgumentParser(   
            description="External parallel sort for text files with one integer per line."
    )
    parser.add_argument("filename", type=Path)
    parser.add_argument("memory_numbers", type=int, help="maximum number of integers kept in memory")
    parser.add_argument("--output", type=Path, help="default: <input>.sorted<suffix> in the same directory")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--force", action="store_true", help="overwrite output file if it exists")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.filename.resolve()#use the full name of the file's path instead of the shorten ones
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    output_path = (args.output.resolve() if args.output else default_output_path(input_path))
    if input_path == output_path:
        raise ValueError("output path must be different from input path")#防止输入输出文件相同

    external_text_sort(
            input_path=input_path,
            output_path=output_path,
            memory_numbers=args.memory_numbers,
            workers=args.workers,
            force=args.force,
        )
    print(output_path)


if __name__ == "__main__":
    mp.freeze_support()
    main()
