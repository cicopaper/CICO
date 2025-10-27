from parser.py_parser import PyParser
from parser.java_parser import JavaParser
from parser.go_parser import GoParser
from parser.base_parser import BaseParser

def extract_sig_py(func_str, func_node, parser):
    try:
        body_node = func_node.children[0].child_by_field_name('body')
        doc_node = parser.get_doc_node(body_node)
        func_start = func_node.start_point[0]
        doc_end = doc_node.end_point[0]
        sig_lines = doc_end - func_start + 1
        func_lines = func_str.split('\n')
        return '\n'.join(func_lines[:sig_lines])
    except Exception as e:
        print(f"Error in get_sig_py: {e}")
        return func_str
def extract_sig(func_str, commented_func_node, parser):
    try:
        funcs = parser.extract_func_list(commented_func_node)
        if len(funcs) == 0:
            return func_str
        commented_func = funcs[0]
        body = commented_func['body']
        signature = func_str.replace(body, '').strip()
        signature = commented_func['doc'] + '\n' + signature
        return signature
    except Exception as e:
        print(f"Error in get_sig: {e}")
        return func_str

def extract_comment2code(func_str, anno='//'):
    lines = func_str.split('\n')
    comment2code= []
    last_line_comment = False
    cur_comment, cur_code = '', ''
    for l in lines:
        if l.strip().startswith(anno): # 开始一个新的注释代码循环
            if cur_code.strip() != '' and cur_comment.strip() != '': # 之前已经收集了一段代码
                comment2code.append((cur_comment, cur_comment + '\n' + cur_code))
                cur_comment, cur_code = '', ''
            cur_comment += l + '\n'
        else:
            cur_code += l + '\n'
    if cur_code.strip() != '' and cur_comment.strip() != '':
        comment2code.append((cur_comment, cur_code))
    return comment2code

def get_comment_list(code, anno='#'):
    lines = code.split('\n')
    comment_list = []
    last_line_comment = False
    for l in lines:
        if l.strip().startswith(anno):
            if last_line_comment:
                comment_list[-1] += '\n' + l
            else:
                comment_list.append(l)
                last_line_comment = True
        else:
            last_line_comment = False
    return comment_list

def split(func_data: dict, parser: BaseParser, get_sig, anno: str):
    """
    lines > 5: sig->func, comment->code block
    lines <=5: sig->func
    """
    comment_to_code = []
    # func sig -> func body, comment -> code block
    if func_data['commented_code'] is None or len(func_data['commented_code']) == 0:
        comment_to_code.append((func_data['func_str'], func_data['func_str']))
        return comment_to_code

    commented_code = func_data['commented_code']
    origin_code = func_data['func_str']
    commented_func_node = parser.parse_code(commented_code)
    # sig -> func
    sig = get_sig(commented_code, commented_func_node, parser)
    comment_to_code.append((sig, origin_code))

    # comment -> code block
    comment_list = get_comment_list(commented_code, anno)
    for c in comment_list:
        comment_to_code.append((c, origin_code))
    return comment_to_code
    # cur_comment_list = extract_comment2code(commented_code, anno)
    # comment_to_code.extend(cur_comment_list)
    # return comment_to_code


def split_func(func_data: dict, lang: str):
    if lang == 'py':
        parser = PyParser()
        return split(func_data, parser, extract_sig_py, '#')
    elif lang == 'java':
        parser = JavaParser()
        return split(func_data, parser, extract_sig, '//')
    elif lang == 'go':
        parser = GoParser()
        return split(func_data, parser, extract_sig, '//')