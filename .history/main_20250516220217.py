import webview
import json
import os
import requests
from dotenv import load_dotenv

# 在脚本的早期加载 .env 文件中的环境变量
load_dotenv()

# 全局的提示词模板基础部分 - 已更新为请求行号
PROMPT_TEMPLATE_BASE = """你是一个专业的Web前端开发助手。你的任务是分析用户提供的HTML代码，并将其分解为在逻辑上相对独立的、可复用的模块。

对于给定的HTML代码：
1.  请识别出主要的、语义清晰的页面区域，例如页眉 (header)、导航 (navigation)、主要内容区 (main content)、侧边栏 (sidebar)、页脚 (footer) 以及其他显著的内容块。
2.  为每个识别出的模块定义一个唯一的、简洁的英文ID (例如: "header_module", "main_content_article_1")。
3.  为每个模块提供一个简短的中文描述。
4.  关键：为每个模块提供其在原始HTML代码中的起始行号 (start_line) 和结束行号 (end_line)。行号从1开始计数。
    - "start_line": 模块开始的行号 (整数)。
    - "end_line": 模块结束的行号 (整数)。
    - 确保 start_line <= end_line。
5.  同时，为每个模块定义清晰的起始和结束注释的 *文本内容* (不包含 '')。
    - "start_comment_text": "LLM_MODULE_START: [模块ID]"
    - "end_comment_text": "LLM_MODULE_END: [模块ID]"
6.  根据页面的复杂度和主要功能区域，建议一个应该被用户优先关注和修改的模块数量 (module_count_suggestion)，这个数量不要超过10个（但可以少于10个）。

请以JSON格式返回你的分析结果，结构如下，请确保所有字符串值都是完整且正确闭合的：

{
  "module_count_suggestion": <建议处理的模块数量 (整数)>,
  "definitions": [
    {
      "id": "<模块ID (字符串)>",
      "description": "<模块中文描述 (字符串)>",
      "start_line": <起始行号 (整数)>,
      "end_line": <结束行号 (整数)>,
      "start_comment_text": "LLM_MODULE_START: <与上面id字段相同的模块ID>",
      "end_comment_text": "LLM_MODULE_END: <与上面id字段相同的模块ID>"
    }
    // ...更多模块定义
  ]
}

例如，如果一个header模块从第5行开始，到第10行结束，其id是 "page_header", 那么对应的定义应该是：
{
  "id": "page_header",
  "description": "页面头部",
  "start_line": 5,
  "end_line": 10,
  "start_comment_text": "LLM_MODULE_START: page_header",
  "end_comment_text": "LLM_MODULE_END: page_header"
}

以下是需要你分析的HTML代码（行号从1开始）：
```html
{user_html_code_with_line_numbers}
```

请再次确认，你的输出必须是严格的JSON格式。
"""

DEFAULT_API_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "default_model": "deepseek/deepseek-chat-v3-0324:free", 
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 120,
    "llm_temperature": 0.1,
    "llm_max_tokens": 4096, 
    "max_modules_to_process_frontend": 10 
}

class Api:
    def __init__(self):
        self.original_html_content_py = "" # 将存储带有注入注释的HTML
        self.api_config = self._load_api_config()
        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app")
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3")
        self.openrouter_api_key = None

    def _load_api_config(self, config_path="api_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"成功加载API配置文件: {config_path}")
                return {**DEFAULT_API_CONFIG, **config}
        except FileNotFoundError:
            print(f"警告: API配置文件 '{config_path}' 未找到，将使用默认配置。")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            print(f"警告: API配置文件 '{config_path}' 格式错误，将使用默认配置。")
            return DEFAULT_API_CONFIG
        except Exception as e:
            print(f"警告: 加载API配置文件时发生错误: {e}，将使用默认配置。")
            return DEFAULT_API_CONFIG

    def get_prompt_template_for_frontend(self):
        # 前端可能不需要看到带行号的模板，但保持此函数以防万一
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code_with_line_numbers}", "[用户提供的HTML代码将在此处由后端插入]")

    def _inject_comments_by_line_numbers(self, original_html, definitions):
        if not definitions:
            return original_html

        lines = original_html.splitlines(True) # 保留换行符

        # 验证并准备定义：确保行号有效且存在注释文本
        valid_definitions = []
        for defi in definitions:
            start_line = defi.get("start_line")
            end_line = defi.get("end_line")
            start_comment_text = defi.get("start_comment_text")
            end_comment_text = defi.get("end_comment_text")

            if not (isinstance(start_line, int) and isinstance(end_line, int) and \
                    start_comment_text and end_comment_text and \
                    1 <= start_line <= end_line <= len(lines)):
                print(f"警告 (_inject_comments_by_line_numbers): 模块 '{defi.get('id', 'Unknown')}' 的行号或注释文本无效/缺失。跳过。 "
                      f"SL:{start_line}, EL:{end_line}, TotalLines:{len(lines)}")
                continue
            valid_definitions.append(defi)
        
        # 按起始行号降序排序，以便从文件末尾开始插入，避免行号错乱
        # 如果起始行号相同，则按结束行号升序排序（优先处理小范围的嵌套模块）
        sorted_definitions = sorted(
            valid_definitions,
            key=lambda x: (x["start_line"], -x["end_line"]), # 主要按 start_line 升序，然后 end_line 降序 (处理嵌套时，外层先)
            reverse=True # 从后往前处理
        )
        
        print(f"DEBUG (_inject_comments_by_line_numbers): 排序后的定义 (将从后往前处理): {[d['id'] for d in sorted_definitions]}")

        for defi in sorted_definitions:
            module_id = defi.get("id")
            start_line_1based = defi["start_line"]
            end_line_1based = defi["end_line"]
            start_comment_actual_text = defi["start_comment_text"] # 这是注释的文本内容
            end_comment_actual_text = defi["end_comment_text"]     # 这是注释的文本内容

            # 构建完整的HTML注释
            start_comment_tag = f"\n" # 加换行符
            end_comment_tag = f"\n" # 加换行符 (如果原始行尾没有换行，这个\n可能需要调整)
            
            # 转换为0-based索引
            # 结束标记应插入在 end_line_1based 指定的行的 *之后*
            # 开始标记应插入在 start_line_1based 指定的行的 *之前*
            
            # 插入结束标记: 在第 end_line_1based 行之后插入
            # 如果 end_line_1based 是最后一行，则在其后追加
            # 列表索引是0-based，所以第N行是 lines[N-1]
            # 我们要在 lines[end_line_1based - 1] 这一行的内容之后插入注释
            # list.insert(index, element) 会将 element 插入到 index 位置，原有元素后移
            
            # 在原始的 end_line_1based 之后插入结束注释
            # 注意：由于我们从后往前插入，这里的行号是相对于当前 `lines` 列表状态的
            # 但因为我们是按原始行号排序从后往前，所以每次操作时的行号可以认为是准确的
            
            # 确保行尾有换行符，再插入注释
            if lines[end_line_1based - 1].endswith('\n'):
                lines.insert(end_line_1based, end_comment_tag) # 在下一行插入
            else: # 如果原始行没有换行符，先加上，再插入注释
                lines[end_line_1based -1] += '\n'
                lines.insert(end_line_1based, end_comment_tag)

            # 插入开始标记: 在第 start_line_1based 行之前插入
            lines.insert(start_line_1based - 1, start_comment_tag)
            
            print(f"DEBUG (_inject_comments_by_line_numbers): 已为模块 '{module_id}' 在行 {start_line_1based}-{end_line_1based} 注入注释。")

        return "".join(lines)

    def _extract_module_content_from_string(self, html_string_with_comments, module_def):
        module_id = module_def.get('id','N/A')
        # 现在 module_def 包含 start_comment_text 和 end_comment_text
        start_comment_text_from_def = module_def.get('start_comment_text', '').strip() 
        end_comment_text_from_def = module_def.get('end_comment_text', '').strip()   

        if not start_comment_text_from_def or not end_comment_text_from_def:
            print(f"DEBUG (_extract_module_content_from_string): 模块 '{module_id}' 缺少 start_comment_text 或 end_comment_text。跳过提取。")
            return ""

        # 构建完整的HTML注释标记进行查找
        start_marker = f""
        end_marker   = f""

        start_index = html_string_with_comments.find(start_marker)
        if start_index == -1:
            # print(f"DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的起始标记 '{start_marker}'。")
            return ""

        # 内容的起始位置是起始标记之后。我们可能需要跳过紧随标记的换行符。
        content_start_index = start_index + len(start_marker)
        if html_string_with_comments[content_start_index:].startswith('\n'):
            content_start_index +=1
        
        end_index = html_string_with_comments.find(end_marker, content_start_index)
        if end_index == -1:
            # print(f"DEBUG (_extract_module_content_from_string): 未找到模块 '{module_id}' 的结束标记 '{end_marker}'。")
            return ""
        
        # 内容的结束位置是结束标记之前。我们可能需要去除标记前的换行符。
        content_end_index = end_index
        if html_string_with_comments[:content_end_index].endswith('\n'):
             content_end_index -=1
             # Check if it ends with the comment tag's preceding newline
             # The actual content should not include the newline that _inject_comments_by_line_numbers might add before the end_marker.
             # This logic is tricky. Let's assume strip() handles it.

        extracted = html_string_with_comments[content_start_index:end_index].strip() # strip() is important here
        return extracted

    def _generate_skeleton_from_string(self, html_string_with_comments, modules_to_skeletonize):
        skeleton = html_string_with_comments
        for i, module_def in enumerate(modules_to_skeletonize):
            module_id = module_def.get('id', f'unknown_module_{i}').strip() 
            start_comment_text_from_def = module_def.get('start_comment_text', '').strip()
            end_comment_text_from_def = module_def.get('end_comment_text', '').strip()

            if not start_comment_text_from_def or not end_comment_text_from_def:
                continue

            start_marker = f""
            end_marker   = f""
            placeholder  = f""

            # We need to find the full block including the markers and the newline characters
            # that _inject_comments_by_line_numbers added.
            
            # Find start_marker (e.g., "\n")
            # Find end_marker (e.g., "\n")
            
            # A more robust way to define the block to replace:
            # Find start_marker. The block starts there.
            # Find end_marker *after* start_marker. The block ends at the end of end_marker.
            
            start_idx = skeleton.find(start_marker)
            if start_idx == -1:
                continue
            
            # The content to replace starts with the start_marker
            # and ends with the end_marker, including the newlines added during injection.
            
            # Find the end of the start_marker (which includes its trailing newline)
            block_content_start_idx = start_idx + len(start_marker)
            if skeleton[block_content_start_idx:].startswith('\n'): # Account for newline after start marker
                 block_content_start_idx +=1

            # Find the beginning of the end_marker
            end_marker_search_start_idx = block_content_start_idx
            end_marker_actual_start_idx = skeleton.find(end_marker, end_marker_search_start_idx)

            if end_marker_actual_start_idx == -1:
                continue
            
            # The full block to replace is from the beginning of start_marker
            # to the end of end_marker.
            # The placeholder should replace this entire segment.
            
            # The segment to replace is from start_idx to (end_marker_actual_start_idx + len(end_marker))
            # However, our injected end_marker was "\n"
            # So, the actual end_marker string is just ""
            # The replacement should cover from the start of the start_marker
            # to the end of the end_marker.

            # Let's try to find the start_marker and then the end_marker after it.
            # The content to replace is from the beginning of start_marker to the end of end_marker.
            
            current_search_pos = 0
            temp_skeleton = skeleton
            while True:
                start_idx_current_loop = temp_skeleton.find(start_marker, current_search_pos)
                if start_idx_current_loop == -1:
                    break # No more occurrences of this start_marker

                end_idx_current_loop = temp_skeleton.find(end_marker, start_idx_current_loop + len(start_marker))
                if end_idx_current_loop == -1:
                    # This start_marker doesn't have a corresponding end_marker after it in the remaining string.
                    # This shouldn't happen if injection was correct. Move search past this broken marker.
                    current_search_pos = start_idx_current_loop + len(start_marker)
                    continue
                
                # Found a valid pair
                content_to_replace_with_markers = temp_skeleton[start_idx_current_loop : end_idx_current_loop + len(end_marker)]
                # Replace only the first found valid block to avoid issues with identically defined nested modules (if any)
                skeleton = skeleton.replace(content_to_replace_with_markers, placeholder, 1)
                break # Processed this module, move to the next module_def
            
        return skeleton

    def analyze_html(self, original_code):
        print("Python API: analyze_html 调用。")
        raw_original_code = original_code 

        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"DEBUG: 在 analyze_html 中, API Key 是: {'SET' if self.openrouter_api_key else 'NOT SET'}")

        llm_response_data = None
        html_with_injected_comments = raw_original_code # Default if LLM fails

        # Add line numbers to the HTML for the LLM prompt
        lines_for_llm = original_code.splitlines()
        html_for_llm_prompt = "\n".join([f"{i+1}: {line}" for i, line in enumerate(lines_for_llm)])
        
        if not self.openrouter_api_key:
            print("警告: OPENROUTER_API_KEY 环境变量未设置。将使用模拟LLM数据。")
            # Simulate LLM response with line numbers
            mock_defs = [
                {"id": "header_mock", "description": "模拟页眉", "start_line": 2, "end_line": 2, "start_comment_text": "LLM_MODULE_START: header_mock", "end_comment_text": "LLM_MODULE_END: header_mock"},
                {"id": "footer_mock", "description": "模拟页脚", "start_line": 4, "end_line": 4, "start_comment_text": "LLM_MODULE_START: footer_mock", "end_comment_text": "LLM_MODULE_END: footer_mock"}
            ]
            # Corresponding raw HTML for mock data (lines are 1-based for LLM)
            # Line 1: <body>
            # Line 2: <header><h1>模拟页眉内容</h1></header>
            # Line 3: <div>一些中间内容</div>
            # Line 4: <footer><p>模拟页脚内容</p></footer>
            # Line 5: </body>
            raw_mock_html_input = "<body>\n<header><h1>模拟页眉内容</h1></header>\n<div>一些中间内容</div>\n<footer><p>模拟页脚内容</p></footer>\n</body>"
            
            llm_response_data = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            print(f"DEBUG: 使用模拟数据。原始模拟HTML (用于注入注释): '{raw_mock_html_input[:200]}...'") 
            if llm_response_data and "definitions" in llm_response_data:
                 html_with_injected_comments = self._inject_comments_by_line_numbers(raw_mock_html_input, llm_response_data["definitions"])
            print(f"DEBUG: 模拟数据处理后，带注入注释的HTML: \n{html_with_injected_comments[:350]}...")
        else:
            current_llm_model = os.getenv("DEFAULT_LLM_MODEL", self.api_config.get("default_model"))
            print(f"OpenRouter API密钥已加载。准备调用LLM (模型: {current_llm_model})...")
            
            # Use html_for_llm_prompt which has line numbers
            full_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code_with_line_numbers}", html_for_llm_prompt)
            
            request_headers = self.api_config.get("base_headers", {}).copy()
            request_headers["Authorization"] = f"Bearer {self.openrouter_api_key}"
            if self.site_url: request_headers["HTTP-Referer"] = self.site_url
            if self.site_name: request_headers["X-Title"] = self.site_name
            request_data = {
                "model": current_llm_model,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": self.api_config.get("llm_temperature", 0.1),
                "max_tokens": self.api_config.get("llm_max_tokens", 4096),
            }
            api_url = self.api_config.get("api_url")
            timeout = self.api_config.get("request_timeout_seconds", 120)

            if not api_url:
                print("错误: API URL 未在配置文件中定义。")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": "API URL配置缺失。", "active_module_definitions": [], "html_skeleton": raw_original_code}

            try:
                print(f"发送到 OpenRouter. URL: {api_url}, 模型: {request_data['model']}")
                response = requests.post(api_url, headers=request_headers, data=json.dumps(request_data), timeout=timeout)
                response.raise_for_status() 
                response_json = response.json() 
                
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    message_content = response_json['choices'][0].get('message', {}).get('content')
                    if message_content:
                        raw_llm_output_json_str = message_content 
                        cleaned_json_str = raw_llm_output_json_str.strip()
                        if cleaned_json_str.startswith("```json"):
                            cleaned_json_str = cleaned_json_str[len("```json"):].lstrip()
                        elif cleaned_json_str.startswith("```"):
                            cleaned_json_str = cleaned_json_str[len("```"):].lstrip()
                        if cleaned_json_str.endswith("```"):
                            cleaned_json_str = cleaned_json_str[:-len("```")].rstrip()
                        llm_response_data = json.loads(cleaned_json_str)
                    else:
                        raise KeyError("LLM响应缺少 'content' 字段")
                else:
                    raise KeyError("LLM响应缺少 'choices' 字段")

                print("\nDEBUG: 解析后的LLM响应数据 (llm_response_data):")
                print(json.dumps(llm_response_data, indent=2, ensure_ascii=False))
                
                if llm_response_data and "definitions" in llm_response_data:
                    # Use raw_original_code for injecting comments, not the one with line numbers
                    html_with_injected_comments = self._inject_comments_by_line_numbers(raw_original_code, llm_response_data["definitions"])
                    print(f"DEBUG: LLM处理后，带注入注释的HTML (前350字符): \n{html_with_injected_comments[:350]}...")
                else:
                    print("警告: LLM响应中无定义，无法添加注释标记。将使用原始HTML。")
                    # html_with_injected_comments remains raw_original_code

            except Exception as e: # Catch more general exceptions last
                print(f"Python API: LLM分析或注释注入过程中发生错误: {e}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"LLM处理错误: {str(e)}", "active_module_definitions": [], "html_skeleton": raw_original_code}

        # This will now store the HTML with comments injected based on line numbers
        self.original_html_content_py = html_with_injected_comments
        
        if not llm_response_data or "definitions" not in llm_response_data:
            print("错误: LLM响应数据不完整或格式不正确 (在最终检查中)。")
            return {"status": "error", "message": "LLM响应数据不完整或格式不正确。", "active_module_definitions": [], "html_skeleton": self.original_html_content_py}

        all_defs = llm_response_data.get("definitions", [])
        suggested_count = llm_response_data.get("module_count_suggestion", 0)
        max_allowed_from_config = self.api_config.get("max_modules_to_process_frontend", 10)
        num_to_process = min(suggested_count if suggested_count > 0 else len(all_defs), max_allowed_from_config, len(all_defs))
        
        # Filter definitions to ensure they have the necessary comment texts for extraction
        current_active_module_definitions = [
            d for d in all_defs[:num_to_process] 
            if d.get("start_comment_text") and d.get("end_comment_text")
        ]
        if len(current_active_module_definitions) != num_to_process:
            print(f"警告: 某些模块定义缺少必要的 start/end_comment_text，已从处理列表中移除。")


        processed_active_definitions = []
        print("\n--- 开始处理模块定义 (基于带注入注释的HTML) ---")
        for module_def in current_active_module_definitions:
            module_id = module_def.get('id', 'N/A')
            # These texts are used to build the full comment string for finding
            llm_start_comment_text = module_def.get('start_comment_text','').strip()
            llm_end_comment_text = module_def.get('end_comment_text','').strip()
            
            actual_start_marker = f""
            actual_end_marker = f""
            
            # _extract_module_content_from_string now uses self.original_html_content_py (which has comments injected by line numbers)
            # and module_def (which contains start_comment_text and end_comment_text)
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)
            
            print(f"DEBUG: 模块ID '{module_id}':")
            print(f"  期望的起始标记 (用于查找): '{actual_start_marker}'")
            print(f"  期望的结束标记 (用于查找): '{actual_end_marker}'")
            if not content and (llm_start_comment_text and llm_end_comment_text): 
                 print(f"  警告: original_content 为空。检查 self.original_html_content_py (前350字符: \n{self.original_html_content_py[:350]}...\n) 中是否存在标记并正确界定内容。")
            print(f"  提取到的 original_content (前100字符): '{content[:100]}...' (长度: {len(content)})")
            processed_active_definitions.append({**module_def, "original_content": content}) 
        print("--- 结束处理模块定义 ---\n")

        skeleton = self._generate_skeleton_from_string(self.original_html_content_py, current_active_module_definitions)

        print("\nDEBUG: 处理后的活动模块定义 (将发送到前端):")
        print(json.dumps(processed_active_definitions, indent=2, ensure_ascii=False))
        print("---------------------------------------------------\n")

        print("\nDEBUG: 生成的HTML骨架 (将发送到前端):")
        print(skeleton if skeleton else "骨架为空或生成失败。")
        print("---------------------------------------------------\n")

        return {
            "status": "success",
            "message": f"LLM分析完成：识别到 {len(all_defs)} 个潜在模块，将处理 {len(current_active_module_definitions)} 个。",
            "active_module_definitions": processed_active_definitions,
            "html_skeleton": skeleton
        }

    def integrate_html(self, skeleton_html, modified_modules_json_string):
        print("Python API: integrate_html 调用。")
        try:
            modified_modules = json.loads(modified_modules_json_string)
        except json.JSONDecodeError as e:
            print(f"错误: 解析 modified_modules_json_string 时发生JSONDecodeError: {e}")
            return {"status": "error", "message": f"无效的JSON (modified_modules): {e}", "final_html": skeleton_html}

        final_html = skeleton_html
        if not isinstance(modified_modules, dict):
            print(f"错误: modified_modules 不是一个字典: {type(modified_modules)}")
            return {"status": "error", "message": "modified_modules 格式错误，应为字典。", "final_html": skeleton_html}
            
        for module_id, new_content in modified_modules.items():
            placeholder = f""
            
            new_content_str = str(new_content) if new_content is not None else ""

            if placeholder in final_html:
                final_html = final_html.replace(placeholder, new_content_str)
            else:
                print(f"警告 (integrate_html): 未找到占位符 '{placeholder}'。模块 '{module_id}' 的内容可能未被正确集成。")
        
        return {"status": "success", "final_html": final_html}

if __name__ == '__main__':
    api = Api()
    webview.create_window(
        '代码智能装配流水线',
        'gui.html',
        js_api=api,
        width=1200,
        height=850,
        resizable=True
    )
    webview.start(debug=True)
