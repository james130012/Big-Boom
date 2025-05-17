import webview
import json
import os
import requests
from dotenv import load_dotenv

# 在脚本的早期加载 .env 文件中的环境变量
load_dotenv()

# 全局的提示词模板基础部分
PROMPT_TEMPLATE_BASE = """你是一个专业的Web前端开发助手。你的任务是分析用户提供的HTML代码，并将其分解为在逻辑上相对独立的、可复用的模块。

对于给定的HTML代码：
1.  请识别出主要的、语义清晰的页面区域，例如页眉 (header)、导航 (navigation)、主要内容区 (main content)、侧边栏 (sidebar)、页脚 (footer) 以及其他显著的内容块。
2.  为每个识别出的模块定义一个唯一的、简洁的英文ID (例如: "header_module", "main_content_article_1")。这个ID将用于构建标记。
3.  为每个模块提供一个简短的中文描述。
4.  关键：为每个模块定义清晰的起始和结束标记，并提取该模块的完整、原始HTML内容。
    - 起始标记的文本必须是 "LLM_MODULE_START: [模块ID]"，其中 [模块ID] 是你在第2步中为此模块定义的ID。
    - 结束标记的文本必须是 "LLM_MODULE_END: [模块ID]"，其中 [模块ID] 是你在第2步中为此模块定义的ID。
    - "module_content_html": 必须是原始HTML中该模块对应的、未经修改的、完整的HTML代码片段。请确保这个片段可以被精确地在原始HTML中定位。
    请确保这些标记能够准确地包裹住模块的完整HTML内容。如果原始HTML中已经存在符合此格式的标记，请优先使用它们并确保ID一致，同时依然提供 "module_content_html"。
5.  根据页面的复杂度和主要功能区域，建议一个应该被用户优先关注和修改的模块数量 (module_count_suggestion)，这个数量不要超过10个（但可以少于10个）。

请以JSON格式返回你的分析结果，结构如下，请确保所有字符串值都是完整且正确闭合的：

{
  "module_count_suggestion": <建议处理的模块数量 (整数)>,
  "definitions": [
    {
      "id": "<模块ID (字符串)>",
      "description": "<模块中文描述 (字符串)>",
      "start_comment": "LLM_MODULE_START: <与上面id字段相同的模块ID>",
      "end_comment": "LLM_MODULE_END: <与上面id字段相同的模块ID>",
      "module_content_html": "<原始HTML中此模块的精确内容 (字符串)>"
    }
    // ...更多模块定义
  ]
}

例如，如果一个模块的id是 "hero_section", 那么它的start_comment应该是 "LLM_MODULE_START: hero_section"，end_comment应该是 "LLM_MODULE_END: hero_section"，并且 "module_content_html" 应该包含 "hero_section" 对应的实际HTML代码。

以下是需要你分析的HTML代码：
```html
{user_html_code}
```

请再次确认，你的输出必须是严格的JSON格式，所有字符串都必须用双引号正确包裹并闭合，特别是 "start_comment", "end_comment" 和 "module_content_html" 的值。这些值本身不应包含 ""。
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
        self.original_html_content_py = "" 
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
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户提供的HTML代码将在此处由后端插入]")

    def _add_comments_to_html(self, original_html, definitions):
        if not definitions:
            return original_html

        valid_definitions = [d for d in definitions if d.get("module_content_html") and d.get("start_comment") and d.get("end_comment")]
        sorted_definitions = sorted(
            valid_definitions,
            key=lambda x: len(x["module_content_html"]),
            reverse=True
        )

        modified_html = original_html
        processed_content_hashes = set() 

        for defi in sorted_definitions:
            module_id = defi.get("id")
            content_to_wrap = defi.get("module_content_html","").strip() 
            start_comment_text = defi.get("start_comment","").strip()
            end_comment_text = defi.get("end_comment","").strip()

            if not all([module_id, content_to_wrap, start_comment_text, end_comment_text]):
                print(f"DEBUG (_add_comments_to_html): 跳过模块 {module_id or 'Unknown'}，因为定义字段不完整 (content: '{content_to_wrap[:20]}...', start: '{start_comment_text}', end: '{end_comment_text}')。")
                continue
            
            content_hash = hash(content_to_wrap)
            if content_hash in processed_content_hashes:
                continue

            # --- 关键修正: 正确构建HTML注释标记 ---
            start_marker_tag = f"" # 已更正！
            end_marker_tag = f""   # 已更正！
            # --- 结束关键修正 ---
            
            wrapped_content = f"{start_marker_tag}\n{content_to_wrap}\n{end_marker_tag}"

            try:
                current_pos = 0
                while True:
                    found_at = modified_html.find(content_to_wrap, current_pos)
                    if found_at == -1:
                        if current_pos == 0: 
                           print(f"警告 (_add_comments_to_html): 未能在HTML中找到模块 '{module_id}' 的内容片段进行包裹。内容片段 (前50字符): '{content_to_wrap[:50]}...'")
                        break 

                    prefix_check_start_index = found_at - len(start_marker_tag) - 1 
                    is_already_wrapped_by_this_marker = False
                    if prefix_check_start_index >= 0:
                        potential_prefix = modified_html[prefix_check_start_index : found_at].strip()
                        if potential_prefix == start_marker_tag:
                            suffix_check_start_index = found_at + len(content_to_wrap)
                            potential_suffix_end_index = suffix_check_start_index + len(end_marker_tag) + 1 
                            if potential_suffix_end_index <= len(modified_html) and \
                               modified_html[suffix_check_start_index : potential_suffix_end_index].strip() == end_marker_tag:
                                is_already_wrapped_by_this_marker = True
                    
                    if is_already_wrapped_by_this_marker:
                        current_pos = found_at + len(content_to_wrap) 
                        continue 

                    modified_html = modified_html[:found_at] + wrapped_content + modified_html[found_at + len(content_to_wrap):]
                    print(f"DEBUG (_add_comments_to_html): 已为模块 '{module_id}' 添加注释标记 (在位置 {found_at})。")
                    processed_content_hashes.add(content_hash) 
                    break 
            except Exception as e:
                print(f"错误 (_add_comments_to_html): 在为模块 '{module_id}' 添加注释时发生异常: {e}")
        
        return modified_html

    def _extract_module_content_from_string(self, html_string, module_def):
        module_id = module_def.get('id','N/A')
        start_marker_text = module_def.get('start_comment', '').strip() 
        end_marker_text = module_def.get('end_comment', '').strip()   

        if not start_marker_text or not end_marker_text:
            return ""

        # --- 关键修正: 正确构建HTML注释标记 ---
        start_marker = f"" # 已更正！
        end_marker   = f"" # 已更正！
        # --- 结束关键修正 ---

        start_index = html_string.find(start_marker)
        if start_index == -1:
            return ""

        content_start_index = start_index + len(start_marker)
        end_index = html_string.find(end_marker, content_start_index)

        if end_index == -1:
            return ""

        extracted = html_string[content_start_index:end_index].strip()
        return extracted

    def _generate_skeleton_from_string(self, html_string, modules_to_skeletonize):
        skeleton = html_string
        for i, module_def in enumerate(modules_to_skeletonize):
            module_id = module_def.get('id', f'unknown_module_{i}').strip() 
            start_marker_text = module_def.get('start_comment', '').strip()
            end_marker_text = module_def.get('end_comment', '').strip()

            if not start_marker_text or not end_marker_text:
                continue

            # --- 关键修正: 正确构建HTML注释标记和占位符 ---
            start_marker = f"" # 已更正！
            end_marker   = f"" # 已更正！
            placeholder  = f"" # 已更正！
            # --- 结束关键修正 ---

            start_idx = skeleton.find(start_marker)
            if start_idx == -1:
                continue
            
            end_idx = skeleton.find(end_marker, start_idx + len(start_marker))
            if end_idx == -1:
                continue
            
            content_to_replace_with_markers = skeleton[start_idx : end_idx + len(end_marker)]
            skeleton = skeleton.replace(content_to_replace_with_markers, placeholder, 1) 
        return skeleton

    def analyze_html(self, original_code):
        print("Python API: analyze_html 调用。")
        raw_original_code = original_code 

        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"DEBUG: 在 analyze_html 中, API Key 是: {'SET' if self.openrouter_api_key else 'NOT SET'}")

        llm_response_data = None
        html_to_process = raw_original_code 

        if not self.openrouter_api_key:
            print("警告: OPENROUTER_API_KEY 环境变量未设置。将使用模拟LLM数据。")
            mock_header_content = "<header><h1>模拟页眉内容</h1></header>" 
            mock_footer_content = "<footer><p>模拟页脚内容</p></footer>" 
            raw_mock_html_input = f"<body>\n{mock_header_content}\n<div>一些中间内容</div>\n{mock_footer_content}\n</body>"

            mock_defs = [
                {"id": "header_mock", "description": "模拟页眉", "start_comment": "LLM_MODULE_START: header_mock", "end_comment": "LLM_MODULE_END: header_mock", "module_content_html": mock_header_content},
                {"id": "footer_mock", "description": "模拟页脚", "start_comment": "LLM_MODULE_START: footer_mock", "end_comment": "LLM_MODULE_END: footer_mock", "module_content_html": mock_footer_content}
            ]
            llm_response_data = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
            print(f"DEBUG: 使用模拟数据。原始模拟HTML: '{raw_mock_html_input[:200]}...'") 
            if llm_response_data and "definitions" in llm_response_data:
                 html_to_process = self._add_comments_to_html(raw_mock_html_input, llm_response_data["definitions"])
            print(f"DEBUG: 模拟数据处理后，带注释的HTML: '{html_to_process[:250]}...'") 
        else:
            current_llm_model = os.getenv("DEFAULT_LLM_MODEL", self.api_config.get("default_model"))
            print(f"OpenRouter API密钥已加载。准备调用LLM (模型: {current_llm_model})...")
            full_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code)
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
                    html_to_process = self._add_comments_to_html(raw_original_code, llm_response_data["definitions"])
                    print(f"DEBUG: LLM处理后，带注释的HTML (前250字符): '{html_to_process[:250]}...'")
                else:
                    print("警告: LLM响应中无定义，无法添加注释标记。将使用原始HTML。")

            except requests.exceptions.HTTPError as e_http:
                print(f"Python API: OpenRouter API请求失败 (HTTPError): {e_http}")
                print(f"响应内容: {e_http.response.text if e_http.response else 'N/A'}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"LLM API请求失败: {str(e_http)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except requests.exceptions.RequestException as e_req:
                print(f"Python API: OpenRouter API请求失败: {e_req}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"LLM API请求失败: {str(e_req)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except json.JSONDecodeError as e_json: 
                problematic_string = cleaned_json_str if 'cleaned_json_str' in locals() and cleaned_json_str is not None else (raw_llm_output_json_str if 'raw_llm_output_json_str' in locals() else "N/A")
                print(f"Python API: 解析JSON时出错: {e_json}")
                print(f"导致JSON解析错误的原始文本: {problematic_string}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"返回的JSON格式无效: {str(e_json)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except KeyError as e_key:
                response_json_for_error = response_json if 'response_json' in locals() else "N/A"
                print(f"Python API: LLM返回的JSON缺少关键字段: {e_key}")
                print(f"LLM返回的JSON对象 (导致KeyError的): {json.dumps(response_json_for_error, indent=2, ensure_ascii=False) if isinstance(response_json_for_error, dict) else response_json_for_error}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"LLM返回的JSON缺少字段: {str(e_key)}", "active_module_definitions": [], "html_skeleton": raw_original_code}
            except Exception as e: 
                print(f"Python API: LLM分析或注释添加过程中发生错误: {e}")
                self.original_html_content_py = raw_original_code 
                return {"status": "error", "message": f"LLM处理错误: {str(e)}", "active_module_definitions": [], "html_skeleton": raw_original_code}

        self.original_html_content_py = html_to_process 
        
        if not llm_response_data or "definitions" not in llm_response_data:
            print("错误: LLM响应数据不完整或格式不正确 (在最终检查中)。")
            return {"status": "error", "message": "LLM响应数据不完整或格式不正确。", "active_module_definitions": [], "html_skeleton": self.original_html_content_py}

        all_defs = llm_response_data.get("definitions", [])
        suggested_count = llm_response_data.get("module_count_suggestion", 0)
        max_allowed_from_config = self.api_config.get("max_modules_to_process_frontend", 10)
        num_to_process = min(suggested_count if suggested_count > 0 else len(all_defs), max_allowed_from_config, len(all_defs))
        current_active_module_definitions = all_defs[:num_to_process]

        processed_active_definitions = []
        print("\n--- 开始处理模块定义 (基于带注释的HTML) ---")
        for module_def in current_active_module_definitions:
            module_id = module_def.get('id', 'N/A')
            llm_start_comment_text = module_def.get('start_comment','').strip()
            llm_end_comment_text = module_def.get('end_comment','').strip()
            
            # --- 关键修正: 在日志中也正确构建实际的HTML注释标记 ---
            actual_start_marker = f"" # 已更正！
            actual_end_marker = f""   # 已更正！
            # --- 结束关键修正 ---
            
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)
            
            print(f"DEBUG: 模块ID '{module_id}':")
            print(f"  期望的起始标记: '{actual_start_marker}'")
            print(f"  期望的结束标记: '{actual_end_marker}'")
            if not content and (llm_start_comment_text and llm_end_comment_text): 
                 print(f"  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '{self.original_html_content_py[:250]}...') 中是否存在标记并正确界定内容。")
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
            "message": f"LLM分析完成：识别到 {len(all_defs)} 个潜在模块，将处理 {num_to_process} 个。",
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
            # --- 关键修正: 精确重建占位符 ---
            placeholder = f"" # 已更正！
            # --- 结束关键修正 ---
            
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
