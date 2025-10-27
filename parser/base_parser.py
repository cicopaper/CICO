from tree_sitter import Parser, Node
import os
from abc import ABC, abstractmethod

class BaseParser(ABC):

    """
     {
        "func_node": func,
        "name": self.nodetostr(func_name),
        "body": self.nodetostr(func_body),
        "func": self.nodetostr(func),
        "doc": self.nodetostr(comment_node) + self.nodetostr(doc_node)
    }
    """

    def __init__(self, specific_language, lan_suffix: str):
        self.LANGUAGE = specific_language
        self.parser = Parser(self.LANGUAGE)
        self.function_data = []
        self.lan_suffix = lan_suffix

    def parse_ast(self, file_path: str):
        if os.path.exists(file_path):
            with open(file_path, "r") as file:
                # print(file_path)
                code = file.read()
                tree = self.parser.parse(bytes(code, "utf8"))
                return tree.root_node
        else:
            raise FileNotFoundError("File not found")
    
    def parse_code(self, code: str):
        tree = self.parser.parse(bytes(code, "utf8"))
        return tree.root_node
    
    def extract_func_from_repo(self, repo_path: str):
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(self.lan_suffix) and 'test' not in file.lower() and not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    root_node = self.parse_ast(file_path)
                    fun_list = self.extract_func_list(root_node)
                    for f in fun_list:
                        f['file_path'] = file_path
                    self.function_data.extend(fun_list)
        return self.function_data

    
    def extract_func_from_snippets(self, code_snippets: list):
        for code_data in code_snippets:
            tree = self.parser.parse(bytes(code_data, 'utf8'))
            func_list = self.extract_func_list(tree.root_node)
            self.function_data.extend(func_list)

    def get_all_func_and_comment(self):
        fun_comment_list = []
        comment_code_list = []
        for f in self.function_data:
            comment_list = self.parse_fun_to_comment(f['func_node'])
            if f['doc'] != '':
                fun_comment_list.append({
                    "doc": f['doc'],
                    "signature": self.get_function_signature(f['func_node']),
                    "comments": self.nodestostr([c[0] for c in comment_list])
                })
                comment_code_list.append([fun_comment_list[-1]['doc'], self.nodetostr(f['func_node'])])
            if len(comment_list) == 1:
                comment_code_list.append([comment_list[0][0], self.nodetostr(f['func_node'])])
            else:
                comment_code_list.extend([c for c in comment_list if c[1] != ''])

        comment_code_dict = {}
        for cc in comment_code_list:
            if cc[0] in comment_code_dict:
                comment_code_dict[cc[0]] += cc[1]
            else:
                comment_code_dict[cc[0]] = cc[1]
        return fun_comment_list, comment_code_dict
    
    def nodestostr(self, nodes: list):
        if nodes == None:
            return ""
        return '\n'.join([self.nodetostr(n) for n in nodes])
    
    def nodetostr(self, node: None):
        if node is None:
            return ""
        if isinstance(node,list):
            return self.nodestostr(node)
        elif isinstance(node, str):
            return node
        elif isinstance(node, Node):
            return node.text.decode('utf-8')
        return ""
    
    def get_function_signature(self, func_node: Node):
        func_str = self.nodetostr(func_node)
        body_str = self.nodetostr(func_node.children_by_field_name('body'))
        return func_str[:func_str.index(body_str)]

    @abstractmethod
    def extract_func_list(self, root_node: Node):
        pass

    @abstractmethod
    def parse_fun_to_comment(self, func_node: Node):
        pass
