from tree_sitter import Language, Node
import tree_sitter_python as tspy
from typing import Union, List

from parser.base_parser import BaseParser

class PyParser(BaseParser):
    """
    parse one file into: 1. {file_path: list of [FunctionData | className:[FunctionData]]}
    parse every file's import path
    for each file: parse import info, add all import info into the cur_file_context
    for each file: 
    """
    def __init__(self):
        super().__init__(Language(tspy.language()), '.py')

    def get_doc_node(self, func_body: Node):
        """
        the first expression statement in the function body is the doc node
        """
        if func_body.child_count == 0:
            return None
        first_child = func_body.children[0]
        if first_child.type == "expression_statement":
            if first_child.child_count == 1 and first_child.children[0].type == "string":
                return first_child.children[0]
        return None 

    def extract_func_list(self, root_node: Node):
        func_query = """
        (
            (comment)* @comment
            .
            (function_definition
                name: (identifier)@func_name
                body: (block)@func_body
            )@method
        )
        """

        query = self.LANGUAGE.query(func_query)
        matches = self.run_query(query, root_node)
        func_defs = []
        if matches:
            for match in matches:
                captures = match[1]
                func_name = self.cap_first(captures, "func_name")
                func_body = self.cap_first(captures, "func_body")
                func = self.cap_first(captures, "method")
                comment_node = self.cap_list(captures, "comment")
                doc_node = self.get_doc_node(func_body)
                
                func_defs.append(
                    {
                        "func_node": func,
                        "name": self.nodetostr(func_name),
                        "body": self.nodetostr(func_body),
                        "func": self.nodetostr(func),
                        "doc": self.nodetostr(comment_node) + self.nodetostr(doc_node)
                    }
                )
        return func_defs

    def get_code_block_for_comment(self, comment_node: Node) -> Union[Node, List[Node]]:
        def is_single_line(node):
            return node.start_point[0] == node.end_point[0]

        def get_next_non_comment_sibling(node):
            sibling = node.next_sibling
            while sibling and sibling.type == 'comment':
                sibling = sibling.next_sibling
            return sibling

        # 检查注释是否在行尾
        if comment_node.prev_sibling and comment_node.prev_sibling.end_point[0] == comment_node.start_point[0]:
            return comment_node.prev_sibling

        next_node = get_next_non_comment_sibling(comment_node)
        
        if not next_node:
            return None

        if not is_single_line(next_node):
            return next_node
        
        # 处理单行代码块的情况
        code_block = [next_node]
        current_node = next_node
        line_count = 1

        while line_count < 5:
            next_sibling = current_node.next_sibling
            if not next_sibling:
                break
            if not is_single_line(next_sibling):
                break
            code_block.append(next_sibling)
            current_node = next_sibling
            line_count += 1

        return code_block if len(code_block) > 1 else code_block[0]

    def parse_fun_to_comment(self, func_node: Node):
        comments_query = '(comment)+@comment'
        query = self.LANGUAGE.query(comments_query)
        matches = self.run_query(query, func_node)
        comment_list = []
        if matches:
            for match in matches:
                comment_blocks = self.cap_list(match[1], 'comment')
                comment_str = self.nodetostr(comment_blocks)
                code_blocks = self.get_code_block_for_comment(comment_blocks[-1])
                if code_blocks != None:
                    comment_list.append((comment_str, self.nodetostr(code_blocks)))
        return comment_list
