import os
import tarfile
import argparse
import shutil
from datetime import datetime
import logging
import stat
import glob
from antlr4 import FileStream, CommonTokenStream
from VerilogLexer import VerilogLexer
from VerilogParser import VerilogParser
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import sys

# Set up logging configuration
logging.basicConfig(level=logging.WARNING)

# Create a lock for thread-safe file operations
file_lock = Lock()

def extract_tar_auto(tar_path, extract_dir):
    """
    Thread-safe function to extract tar files automatically detecting compression format.
    Args:
        tar_path: Path to the tar file
        extract_dir: Directory to extract files to
    """
    with file_lock:  # Use lock for thread-safe file operations
        try:
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)
                return
        except tarfile.ReadError:
            try:
                with tarfile.open(tar_path, "r:") as tar:
                    tar.extractall(path=extract_dir)
                    return
            except tarfile.ReadError as e:
                raise Exception(f"Failed to extract '{tar_path}'. Error: {e}")

def remove_comments(file_path, templete_file_path):
    """
    Remove line and block comments as well as preprocessor directives from Verilog files.
    Thread-safe implementation.
    """
    with file_lock:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
            with open(templete_file_path, "r", encoding="utf-8", errors="ignore") as file:
                templet_lines = file.readlines()
            cleaned_lines = []
            inside_block_comment = False
            inside_preprocessor_block = False

            for line in lines:
                if line in templet_lines:
                    continue
                if inside_block_comment:
                    if '*/' in line:
                        inside_block_comment = False
                        line = line.split('*/', 1)[1]
                    else:
                        continue
                if '/*' in line:
                    inside_block_comment = True
                    line = line.split('/*', 1)[0]
                    continue
                
                stripped_line = line.strip()
                if stripped_line.startswith("`ifdef") or stripped_line.startswith("`ifndef") or stripped_line.startswith("`endif"):
                    inside_preprocessor_block = True
                    continue

                if '//' in line:
                    line = line.split('//', 1)[0] + '\n'
                cleaned_lines.append(line)
            return ''.join(cleaned_lines)

        except Exception as e:
            logging.error(f"Failed to clean comments from file '{file_path}': {e}")
            return None

def parse_verilog_file(file_path, templete_file_path):
    """
    Thread-safe function to parse a Verilog file and generate its AST.
    """
    try:
        cleaned_content = remove_comments(file_path, templete_file_path)
        if cleaned_content is None:
            return None

        temp_file_path = f"temp_cleaned_file_{os.getpid()}.v"
        with file_lock:
            with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(cleaned_content)

            input_stream = FileStream(temp_file_path, encoding="utf-8")
            sys.stderr = open(os.devnull, "w")
            
            lexer = VerilogLexer(input_stream)
            token_stream = CommonTokenStream(lexer)
            parser = VerilogParser(token_stream)
            tree = parser.source_text()

            sys.stderr.close()
            sys.stderr = sys.__stderr__
            
            os.remove(temp_file_path)
            return tree
            
    except Exception as e:
        logging.error(f"Failed to parse file '{file_path}': {e}")
        return None

def winnowing_hashes(input_string, n=4, w=5):
    """
    Calculate winnowing hashes with thread safety.
    """
    hashes = []
    for i in range(len(input_string) - n + 1):
        ngram = input_string[i:i+n]
        ngram_hash = hash(ngram)
        hashes.append((ngram_hash, i))

    winnowed_set = set()
    for start_idx in range(0, len(hashes) - w + 1):
        window = hashes[start_idx : start_idx + w]
        min_hash, min_idx = min(window, key=lambda x: (x[0], -x[1]))
        winnowed_set.add((min_hash, min_idx))

    return winnowed_set

def extract_features_from_ast(tree):
    """
    Thread-safe feature extraction from AST.
    """
    if not tree:
        return set()
    try:
        tree_string = tree.toStringTree()
        n = 5
        w = 10
        fingerprints = winnowing_hashes(tree_string, n=n, w=w)
        features = {fp[0] for fp in fingerprints}
        return features

    except Exception as e:
        logging.error(f"Failed to extract features from AST: {e}")
        return set()

def calculate_similarity_with_ast(tree1, tree2):
    """
    Thread-safe similarity calculation between two ASTs.
    """
    try:
        features1 = extract_features_from_ast(tree1)
        features2 = extract_features_from_ast(tree2)
        intersection = len(features1 & features2)
        union = len(features1 | features2)

        # Jaccard index formula
        # similarity = intersection / union if union > 0 else 0

        # intersection =  len(features1 & features2)
        similarity = (intersection / len(features1) + intersection / len(features2)) / 2 if len(features1) > 0 and len(features2) else 0

        return similarity
    except Exception as e:
        logging.error(f"Failed to calculate similarity: {e}")
        return 0

def process_file_pair(file_pair, templete_file_path):
    """
    Process a pair of files for similarity comparison.
    """
    file1, file2 = file_pair
    tree1 = parse_verilog_file(file1, templete_file_path)
    tree2 = parse_verilog_file(file2, templete_file_path)
    
    if not tree1 or not tree2:
        return file1, file2, 0
    
    similarity = calculate_similarity_with_ast(tree1, tree2)
    return file1, file2, similarity

def run_pairwise_ast_comparison(target_file, student_dir, templete_file_path):
    """
    Parallel implementation of AST-based plagiarism detection.
    """
    extracted_dirs = []
    matched_files = []
    
    # Extract all tar files in parallel
    with ThreadPoolExecutor() as executor:
        tar_files = glob.glob(os.path.join(student_dir, "**", "*.tar.gz"), recursive=True)
        futures = []
        
        for student_tar in tar_files:
            extract_dir = os.path.join(
                os.path.dirname(student_tar),
                os.path.basename(student_tar).replace(".tar.gz", "")
            )
            futures.append(
                executor.submit(extract_tar_auto, student_tar, extract_dir)
            )
            extracted_dirs.append(extract_dir)
            
        concurrent.futures.wait(futures)
    
    # Collect all matching files
    for extract_dir in extracted_dirs:
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if not file.startswith("._") and file.endswith(target_file):
                    matched_files.append(os.path.join(root, file))
    
    # Generate file pairs for comparison
    file_pairs = []
    for i, file1 in enumerate(matched_files):
        for j, file2 in enumerate(matched_files):
            if i < j:
                file_pairs.append((file1, file2))
    
    # Process file pairs in parallel
    report = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_file_pair, pair, templete_file_path) for pair in file_pairs]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                report.append(result)
            except Exception as e:
                logging.error(f"Error processing file pair: {e}")
    
    return report, extracted_dirs

def save_ast_report(report, extracted_dirs, report_dir):
    """
    Thread-safe function to save AST report and clean up directories.
    """
    with file_lock:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        report_file_path = os.path.join(report_dir, f"ast_pairwise_report_{timestamp}.txt")
        os.makedirs(report_dir, exist_ok=True)
        
        with open(report_file_path, 'w', encoding="utf-8") as report_file:
            report_file.write("AST Pairwise Plagiarism Detection Report\n")
            report_file.write("=" * 50 + "\n")
            for file1, file2, similarity in sorted(report, key=lambda x: x[2], reverse=True):
                report_file.write(f"Similarity between {file1} and {file2}: {similarity:.2f}\n")
    
    # Clean up extracted directories in parallel
    with ThreadPoolExecutor() as executor:
        executor.map(lambda dir_path: shutil.rmtree(dir_path, ignore_errors=True), extracted_dirs)
    
    logging.info(f"AST pairwise similarity report saved to: {report_file_path}")

def main():
    """
    Main function with argument parsing and execution flow.
    """
    parser = argparse.ArgumentParser(description="AST-based Verilog pairwise plagiarism detection script.")
    parser.add_argument("--target_file", type=str, required=True, help="Target file name to check")
    parser.add_argument("--student_dir", type=str, required=True, help="Directory containing student tar.gz submissions")
    parser.add_argument("--report_dir", type=str, default="report", help="Directory to save the report")
    parser.add_argument("--templete_file", type=str, help="File path of templete file")

    args = parser.parse_args()

    report, extracted_dirs = run_pairwise_ast_comparison(
        target_file=args.target_file,
        student_dir=args.student_dir,
        templete_file_path=args.templete_file
    )

    save_ast_report(report, extracted_dirs, args.report_dir)

if __name__ == "__main__":
    main()