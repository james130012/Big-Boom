import json

def inject_comments_by_line_numbers_minimal(original_html, definitions):
    """
    简化的注释注入函数，用于测试。
    根据LLM的定义，在HTML中插入模块注释标记。
    """
    if not definitions:
        return original_html

    lines = original_html.splitlines(True) 

    valid_definitions = []
    for defi in definitions:
        start_line = defi.get("start_line")
        end_line = defi.get("end_line")
        start_comment_text = defi.get("start_comment_text") 
        end_comment_text = defi.get("end_comment_text")     

        if not (isinstance(start_line, int) and isinstance(end_line, int) and \
                start_comment_text and end_comment_text and \
                1 <= start_line <= end_line <= len(lines)): 
            print(f"MINIMAL_TEST - 警告 (_inject_comments_by_line_numbers): 模块 '{defi.get('id', 'Unknown')}' 的行号或注释文本无效/缺失。跳过。 "
                  f"SL:{start_line}, EL:{end_line}, TotalLines:{len(lines)}, StartText: '{start_comment_text}', EndText: '{end_comment_text}'")
            continue
        valid_definitions.append(defi)
    
    sorted_definitions = sorted(
        valid_definitions,
        key=lambda x: (x["start_line"], x["end_line"]), 
        reverse=True 
    )
    
    print(f"MINIMAL_TEST - DEBUG (_inject_comments_by_line_numbers): 排序后的定义 (将从后往前处理): {[d['id'] for d in sorted_definitions]}")

    for defi in sorted_definitions:
        module_id = defi.get("id")
        start_line_1based = defi["start_line"]
        end_line_1based = defi["end_line"]
        start_comment_actual_text = defi["start_comment_text"] 
        end_comment_actual_text = defi["end_comment_text"]     

        # --- 关键修正: 构建完整的HTML注释标记 ---
        start_comment_tag = f"\n" # 已更正！
        end_comment_tag_to_insert = f"\n" # 已更正！
        # --- 结束关键修正 ---
        
        if end_line_1based -1 < len(lines) and not lines[end_line_1based - 1].endswith('\n'):
            lines[end_line_1based - 1] += '\n'
        
        current_end_comment_tag_with_newline = end_comment_tag_to_insert
        if not current_end_comment_tag_with_newline.endswith('\n'): 
             current_end_comment_tag_with_newline += '\n'
        
        if end_line_1based < len(lines): 
            lines.insert(end_line_1based, current_end_comment_tag_with_newline)
        else: 
            lines.append(current_end_comment_tag_with_newline)

        lines.insert(start_line_1based - 1, start_comment_tag) 
        
        print(f"MINIMAL_TEST - DEBUG (_inject_comments_by_line_numbers): 已为模块 '{module_id}' 在原始行 {start_line_1based}-{end_line_1based} 附近注入注释。")

    return "".join(lines)

def extract_module_content_from_string_minimal(html_string_with_comments, module_def):
    """
    简化的内容提取函数，用于测试。
    """
    module_id = module_def.get('id','N/A')
    start_comment_text_from_def = module_def.get('start_comment_text', '').strip() 
    end_comment_text_from_def = module_def.get('end_comment_text', '').strip()   

    if not start_comment_text_from_def or not end_comment_text_from_def:
        print(f"MINIMAL_TEST - DEBUG (_extract_module_content_from_string): 模块 '{module_id}' 缺少 start_comment_text 或 end_comment_text。跳过提取。")
        return ""

    # --- 关键修正: 构建完整的HTML注释标记进行查找 ---
    start_marker = f"" # 已更正！
    end_marker   = f"" # 已更正！
    # --- 结束关键修正 ---

    start_index = html_string_with_comments.find(start_marker)
    if start_index == -1:
        print(f"MINIMAL_TEST - DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的起始标记 '{start_marker}'。")
        return ""

    content_start_index = start_index + len(start_marker)
    if html_string_with_comments[content_start_index:].startswith('\n'): 
        content_start_index +=1
    
    end_index = html_string_with_comments.find(end_marker, content_start_index)
    if end_index == -1:
        print(f"MINIMAL_TEST - DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的结束标记 '{end_marker}' (在起始标记之后)。")
        return ""
    
    extracted = html_string_with_comments[content_start_index:end_index].strip() 
    return extracted

if __name__ == '__main__':
    print("--- 开始最小测试案例 ---")

    original_html_sample = """<html>
<head>
    <title>测试页</title>
</head>
<body>
    <header>
        <h1>页眉标题</h1>
    </header>
    <nav>
        <ul><li>导航1</li><li>导航2</li></ul>
    </nav>
    <main>
        <p>这是主要内容的第一段。</p>
        <p>这是主要内容的第二段。</p>
    </main>
    <footer>
        <p>页脚信息</p>
    </footer>
</body>
</html>"""
    print("\n--- 原始HTML ---")
    print(original_html_sample)

    llm_definitions_sample = [
        {
            "id": "header_section",
            "description": "页眉区域",
            "start_line": 6, 
            "end_line": 8,   
            "start_comment_text": "LLM_MODULE_START: header_section",
            "end_comment_text": "LLM_MODULE_END: header_section"
        },
        {
            "id": "nav_menu",
            "description": "导航菜单",
            "start_line": 9, 
            "end_line": 11,  
            "start_comment_text": "LLM_MODULE_START: nav_menu",
            "end_comment_text": "LLM_MODULE_END: nav_menu"
        },
        { 
            "id": "main_paragraph_1",
            "description": "主要内容段落1",
            "start_line": 13, 
            "end_line": 13,
            "start_comment_text": "LLM_MODULE_START: main_paragraph_1",
            "end_comment_text": "LLM_MODULE_END: main_paragraph_1"
        },
        {
            "id": "main_content",
            "description": "主要内容",
            "start_line": 12, 
            "end_line": 15,   
            "start_comment_text": "LLM_MODULE_START: main_content",
            "end_comment_text": "LLM_MODULE_END: main_content"
        },
        {
            "id": "footer_section",
            "description": "页脚区域",
            "start_line": 16, 
            "end_line": 18,   
            "start_comment_text": "LLM_MODULE_START: footer_section",
            "end_comment_text": "LLM_MODULE_END: footer_section"
        }
    ]
    print("\n--- LLM 定义 (模拟) ---")
    print(json.dumps(llm_definitions_sample, indent=4, ensure_ascii=False))

    html_with_injected_comments = inject_comments_by_line_numbers_minimal(original_html_sample, llm_definitions_sample)
    print("\n--- 带注入注释的HTML ---")
    print(html_with_injected_comments)

    print("\n--- 提取的模块内容 ---")
    for module_def in sorted(llm_definitions_sample, key=lambda x: x["start_line"]): 
        print(f"\n--- 提取模块ID: {module_def['id']} (原始SL:{module_def['start_line']}) ---")
        extracted_content = extract_module_content_from_string_minimal(html_with_injected_comments, module_def)
        # 即使内容为空字符串也打印，以确认提取函数被正确调用且找到了标记
        print(f"提取到的内容:\n'''\n{extracted_content}\n'''")


    print("\n--- 最小测试案例结束 ---")

