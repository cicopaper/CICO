from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from parser.java_parser import JavaParser as Parser
from data.example import JAVA_EXAMPLE as EXAMPLE
from utils.text_util import extract_code_blocks

SPLIT_MODEL='saves/splitter_all/'
SPLIT_MODEL_URL='http://0.0.0.0:34567/v1'

base_prompt = """
Write comment and doc string for the given code snippet.
** DO NOT write comment line by line, you should add a comment at a sub-module's begining.**.
A submodule refers to a code block or multiple lines of code that are highly semantically coherent and independently accomplish a key sub-function within a function.
Return the code snippet with comments and doc string.
Here is an Example, your response should have the similar comment ratio:
### Example
#### Code to be commented
```
{example_code}
```
#### Code with comments
```
{example_code_with_comment}
```
Here is the code snippet you need to comment:
```
{code_snippet}
```
"""

def remove_all_comment(func_data: dict, parser):
    func_str = parser.nodetostr(func_data['func_node'])
    func_str = func_str.replace(func_data['doc'], '')
    lines = func_str.split('\n')
    for l in lines:
        if l.strip().startswith('//'):
            lines.remove(l)
    return '\n'.join(lines)

def comment(func_str: str, llm: OpenAI):
    query = base_prompt.format(example_code=EXAMPLE[0], example_code_with_comment=EXAMPLE[1], code_snippet=func_str)
    messages = [{"role": "user", "content": query}]
    response = llm.chat.completions.create(
        model=SPLIT_MODEL,
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content

def get_sig2body(func_str, commented_func_node, parser):
    try:
        funcs = parser.extract_func_list(commented_func_node)
        if len(funcs) == 0:
            return (None, None)
        commented_func = funcs[0]
        body = commented_func['body']
        signature = func_str.replace(body, '').strip()
        
        return [signature, commented_func['body'] ]
    except Exception as e:
        print(f"Error in get_sig2body: {e}")
        return (None, None)

def split_repo(repo_path):
    llm = OpenAI(base_url=SPLIT_MODEL_URL, api_key='...')
    parser = Parser()
    parser.extract_func_from_repo(repo_path)
    all_func_data = parser.function_data
    for d in all_func_data:
        d['pure_func'] = remove_all_comment(d, parser)
        d.pop('func_node')
    
    with tqdm(total=len(all_func_data)) as pbar:
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_func = {executor.submit(comment, d['pure_func'], llm): d for d in all_func_data}
            for future in as_completed(future_to_func):
                func_data = future_to_func[future]
                try:
                    result = future.result()
                    func_data['commented_code'] = extract_code_blocks(result)
                except Exception as exc:
                    print(f'Function {func_data["name"]} generated an exception: {exc}')
                pbar.update(1)
    comment_to_code = []
    # func sig -> func body, comment -> code block
    for d in all_func_data:
        if d['commented_code'] is None or len(d['commented_code']) == 0:
            comment_to_code.extend((d['pure_func'], d['pure_func']))
            continue
        commented_func_node = parser.parse_code(d['commented_code'])
        # comment -> code block
        cur_comment_list = parser.parse_fun_to_comment(commented_func_node)
        comment_to_code.extend(cur_comment_list)

        # func sig -> func body
        sig2body = get_sig2body(d['commented_code'], commented_func_node, parser)
        if sig2body[0] is not None:
            comment_to_code.append(sig2body)
    return comment_to_code