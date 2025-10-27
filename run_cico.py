import json
import argparse

import pandas as pd
from utils.text_util import extract_code_blocks
from rag.indexer import Vector_Faiss
from tqdm import tqdm
if LANGUAGE == 'py':
    from rag.splitter_py import split_repo
    from parser.py_parser import PyParser as Parser
elif LANGUAGE == 'java':    
    from rag.splitter_java import split_repo
    from parser.java_parser import JavaParser as Parser
elif LANGUAGE == 'go':
    from rag.splitter_go import split_repo
    from parser.go_parser import GoParser as Parser

parser = argparse.ArgumentParser()
parser.add_argument('--repo_path', type=str, default='../MRG/repo/py_data/sample_repo')
parser.add_argument('--language', type=str, default='py')

args = parser.parse_args()
repo_path = args.repo_path
LANGUAGE = args.language

def build_index_from_repo(repo_path):
    parser = Parser()
    func_list = parser.extract_func_from_repo(repo_path)
    indexer = Vector_Faiss()
    docs = []
    for f in func_list:
        func_str = parser.nodetostr(f['func_node'])
        docs.append({
            'key': func_str,
            'value': func_str
        })
    indexer.add_docs(docs)
    return indexer

def cico_pipeline(repo_path, tasks):
    """
    run cico index and retrieve for a repo then return all retrieved results for a task list
    """
    comment_indexer = build_index_from_repo(repo_path)
    code_indexer = build_index_from_repo(repo_path)
    for task in tqdm(tasks, total=len(tasks)):
        retr_cs = []
        for c in task['comments']:
            com_r = comment_indexer.search_query(c, top_k=2)
            retr_cs.extend(com_r)

        cur_codes = []
        sig_r = code_indexer.search_query(task['signature'], top_k=5)
        cur_codes.extend(sig_r)
        all_retrieves = list(set(retr_cs + cur_codes))
        all_retrieves = sorted(all_retrieves, key=lambda x: x['score'], reverse=True)[:5]
        task['retrieves'] = all_retrieves
    return tasks

if __name__ == "__main__":
    
    tasks = [
        {
            'signature': 'def add(a, b):',
            'comments': ['This function adds two numbers together.']
        }
    ]
    tasks = cico_pipeline(repo_path, tasks)
    