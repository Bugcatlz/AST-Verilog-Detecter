# AST-based Verilog Pairwise Similarity Detection

This project uses **[ANTLR4](https://www.antlr.org/)** with a custom `VerilogLexer` and `VerilogParser` to generate Abstract Syntax Trees (ASTs) from Verilog files. It then applies **Winnowing** for similarity comparison, enabling plagiarism detection between Verilog submissions.

Unlike services like **MOSS**, which upload code to external servers, this tool runs locally, ensuring code privacy.

---

## Table of Contents
1. [Features](#features)  
2. [Requirements](#requirements)  
3. [Usage](#usage)  
    - [Command-line Arguments](#command-line-arguments)  
    - [Examples](#examples)  
    - [Output](#output)  
4. [Troubleshooting](#troubleshooting)  
5. [Acknowledgments](#acknowledgments)  

---

## Features
- **Multithreading**: Utilizes `ThreadPoolExecutor` for parallel AST parsing and similarity calculations.
- **Automatic Extraction**: Finds and extracts `*.tar.gz` files into individual folders.
- **Preprocessing**: Removes comments, macros (`ifdef`/`ifndef`/`endif`), and noise before AST generation.
- **AST Parsing**: Leverages [ANTLR4 Verilog Grammar](https://github.com/antlr/grammars-v4/tree/master/verilog) to generate Verilog syntax trees.
- **Similarity Calculation**: Uses the **Winnowing** algorithm to calculate fingerprints from ASTs and compute approximate **Jaccard similarity**.
- **Report Generation**: Outputs a timestamped report showing similarity scores for all file pairs.

---

## Requirements

1. **Python 3.6+**  
2. **ANTLR4** and Python runtime support  
   - Install via `pip install antlr4-tools` or follow the [ANTLR4 official guide](https://www.antlr.org/).  
3. **Verilog Lexer/Parser**  
   - You can either generate `VerilogLexer.py` and `VerilogParser.py` using the [ANTLR4 Verilog Grammar](https://github.com/antlr/grammars-v4/tree/master/verilog) or use the pre-generated files provided in this project.  
   - If you choose to generate them yourself, ensure you are using the same ANTLR4 version as referenced in this project to maintain compatibility. Additionally, ensure the class names in the generated files match the script references.  
4. **Other Python Libraries** (available via standard library or `pip`):  
   - `tarfile`
   - `argparse`
   - `datetime`
   - `logging`
   - `shutil`
   - `glob`
   - `concurrent.futures`
   - `threading`  
   - `sys`

---

## Usage

Place `main.py`, `VerilogLexer.py`, and `VerilogParser.py` in the same directory. Then, run the script:

```
python main.py \
    --target_file <target Verilog file name> \
    --student_dir <directory containing student submissions> \
    --report_dir <directory to save the report> \
    --templete_file <path to template file (optional)>
```

### Arguments

| **Argument**         | **Description**                                                          | **Required** | **Example**                          |
|----------------------|--------------------------------------------------------------------------|--------------|--------------------------------------|
| `--target_file`      | The target Verilog file name to search for and compare.                  | **Yes**      | `--target_file lab1.v`               |
| `--student_dir`      | Directory containing student submissions (searches recursively).         | **Yes**      | `--student_dir ./submissions`        |
| `--report_dir`       | Directory to save the report (default: `report`).                        | No           | `--report_dir ./ast_reports`         |
| `--templete_file`    | Optional template file to exclude shared code lines during preprocessing.| No           | `--templete_file ./template.v`       |

---

### Examples
Assume your project structure is as follows:
```
├── VerilogLexer.py
├── VerilogParser.py
├── main.py
├── template.v
├── submissions
│   ├── studentA
│   │   └── studentA-lab1.tar.gz
│   └── studentB
│       └── studentB-lab1.tar.gz
```

#### Example 1: **Pairwise Comparison with Template Exclusion**

If `lab1.v` is the target file for comparison, and a `template.v` is provided to exclude shared code:
```
python main.py \
    --target_file lab1.v \
    --student_dir ./submissions \
    --templete_file ./template.v \
    --report_dir ./ast_reports
```

This command:
1. Extracts `studentA-lab1.tar.gz`, `studentB-lab1.tar.gz`, etc.
2. Searches for files named `lab1.v` in all extracted directories.
3. Preprocesses the files (removes comments, macros, and template code).
4. Parses the Verilog files into ASTs and calculates pairwise similarity.
5. Saves the similarity report in `./ast_reports/ast_pairwise_report_<timestamp>.txt.`

### Output
The report will be saved in the specified `report_dir`, with a filename like:
```
./ast_reports/ast_pairwise_report_2024_01_01_14_30_00.txt
```
Sample content:
```
AST Pairwise Plagiarism Detection Report
==================================================
Similarity between submissions/studentA/lab1.v and submissions/studentB/lab1.v: 0.85
Similarity between submissions/studentA/lab1.v and submissions/studentC/lab1.v: 0.72
...
```

## Troubleshooting

### ANTLR Parsing Issues
- Ensure `VerilogLexer.py` and `VerilogParser.py` exist and match the script's imports.
- If generating grammar files, use the correct ANTLR4 version and command.

### Extraction or File Reading Errors
- Verify that `*.tar.gz` files are valid and not corrupted.
- Ensure proper permissions for reading or extracting files.

### Missing Target File
- Check that `--target_file` matches the exact filename in the student submissions.
- Ensure the script searches the correct directories and subdirectories.

### Low Similarity Scores
- Adjust Winnowing parameters (e.g., `n=4, w=5` or `n=5, w=10`) for better granularity.
- Review the preprocessing logic to ensure relevant code is not overly removed during cleanup.


## Acknowledgments

- [ANTLR4 Grammars v4 for Verilog](https://github.com/antlr/grammars-v4/tree/master/verilog) for providing comprehensive grammar support for Verilog.
- This project and its methodology are inspired by the work presented in the paper **"A Search of Verilog Code Plagiarism Detection Method"** by Lisheng Wang, Lingchao Jiang, and Guofeng Qin, published in the *13th International Conference on Computer Science & Education (ICCSE 2018)*. The paper highlights the use of MOSS and Abstract Syntax Tree (AST)-based methods for Verilog code plagiarism detection. It provides significant insights into integrating structural and semantic similarity analysis, which has greatly influenced the design and development of this project.

    For more details, refer to the original paper:
    - **Title**: A Search of Verilog Code Plagiarism Detection Method
    - **Authors**: Lisheng Wang, Lingchao Jiang, and Guofeng Qin
    - **Conference**: 13th International Conference on Computer Science & Education (ICCSE 2018)
    - **DOI**: 10.1109/ICCSE.2018.8468760&#8203;:contentReference[oaicite:0]{index=0}.
