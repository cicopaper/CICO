import re

def extract_code_blocks(markdown_text: str) -> str:
    code_block_pattern = re.compile(r'```.*?\n(.*?)```', re.DOTALL)    
    code_blocks = code_block_pattern.findall(markdown_text)
    if len(code_blocks) == 0:
        return None
    return code_blocks[0]