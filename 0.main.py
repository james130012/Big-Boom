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
4.  关键：为每个模块定义清晰的起始和结束标记。这些标记必须是HTML注释的形式。
    - 起始标记的文本必须是 "LLM_MODULE_START: [模块ID]"，其中 [模块ID] 是你在第2步中为此模块定义的ID。
    - 结束标记的文本必须是 "LLM_MODULE_END: [模块ID]"，其中 [模块ID] 是你在第2步中为此模块定义的ID。
    请确保这些标记能够准确地包裹住模块的完整HTML内容。如果原始HTML中已经存在符合此格式的标记，请优先使用它们并确保ID一致。
5.  根据页面的复杂度和主要功能区域，建议一个应该被用户优先关注和修改的模块数量 (module_count_suggestion)，这个数量不要超过10个（但可以少于10个）。

请以JSON格式返回你的分析结果，结构如下，请确保所有字符串值都是完整且正确闭合的：

{
  "module_count_suggestion": <建议处理的模块数量 (整数)>,
  "definitions": [
    {
      "id": "<模块ID (字符串)>",
      "description": "<模块中文描述 (字符串)>",
      "start_comment": "LLM_MODULE_START: <与上面id字段相同的模块ID>",
      "end_comment": "LLM_MODULE_END: <与上面id字段相同的模块ID>"
    }
    // ...更多模块定义
  ]
}

例如，如果一个模块的id是 "hero_section", 那么它的start_comment应该是 "LLM_MODULE_START: hero_section"，end_comment应该是 "LLM_MODULE_END: hero_section"。

以下是需要你分析的HTML代码：
```html
{user_html_code}
```

请再次确认，你的输出必须是严格的JSON格式，所有字符串都必须用双引号正确包裹并闭合，特别是 "start_comment" 和 "end_comment" 的值。这些值本身不应包含 ""。
"""

DEFAULT_API_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "default_model": "deepseek/deepseek-chat-v3-0324:free", # 默认模型，可以被 .env 覆盖
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 120,
    "llm_temperature": 0.1,
    "llm_max_tokens": 2048,
    "max_modules_to_process_frontend": 10 # UI默认处理的最大模块数
}

class Api:
    def __init__(self):
        self.original_html_content_py = ""
        self.api_config = self._load_api_config()

        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app")
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3")
        self.openrouter_api_key = None # 将在需要时从 .env 加载

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

    def _extract_module_content_from_string(self, html_string, module_def):
        module_id = module_def.get('id','N/A')
        start_marker_text = module_def.get('start_comment', '').strip() 
        end_marker_text = module_def.get('end_comment', '').strip()   

        if not start_marker_text or not end_marker_text:
            return ""

        # --- 关键修正 v9: 正确构建HTML注释标记 ---
        start_marker = f""  # 更正！
        end_marker = f""    # 更正！
        # --- 结束关键修正 v9 ---

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

            # --- 关键修正 v9: 正确构建HTML注释标记和占位符 ---
            start_marker = f""  # 更正！
            end_marker = f""    # 更正！
            placeholder = f"" # 更正！
            # --- 结束关键修正 v9 ---

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
        self.original_html_content_py = original_code

        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        print(f"DEBUG: 在 analyze_html 中, API Key 是: {self.openrouter_api_key}") 

        llm_response_data = None
        raw_llm_output_json_str = None 
        cleaned_json_str = None      

        if not self.openrouter_api_key:
            print("警告: OPENROUTER_API_KEY 环境变量未设置或未在.env文件中找到。将使用模拟LLM数据。")
            mock_defs = [
                {"id": "header_mock", "description": "模拟页眉", "start_comment": "LLM_MODULE_START: header_mock", "end_comment": "LLM_MODULE_END: header_mock"},
                {"id": "footer_mock", "description": "模拟页脚", "start_comment": "LLM_MODULE_START: footer_mock", "end_comment": "LLM_MODULE_END: footer_mock"}
            ]
            llm_response_data = {"module_count_suggestion": len(mock_defs), "definitions": mock_defs}
        else:
            current_llm_model = os.getenv("DEFAULT_LLM_MODEL", self.api_config.get("default_model"))
            print(f"OpenRouter API密钥已加载。准备调用LLM (模型: {current_llm_model})...")

            full_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", original_code)

            request_headers = self.api_config.get("base_headers", {}).copy()
            request_headers["Authorization"] = f"Bearer {self.openrouter_api_key}"
            if self.site_url: request_headers["HTTP-Referer"] = self.site_url
            if self.site_name: request_headers["X-Title"] = self.site_name

            request_data = {
                "model": current_llm_model,
                "messages": [{"role": "user", "content": full_prompt}],
                "temperature": self.api_config.get("llm_temperature", 0.1),
                "max_tokens": self.api_config.get("llm_max_tokens", 2048),
            }
            api_url = self.api_config.get("api_url")
            timeout = self.api_config.get("request_timeout_seconds", 120)

            if not api_url:
                print("错误: API URL 未在配置文件中定义。")
                return {"status": "error", "message": "API URL配置缺失。", "active_module_definitions": [], "html_skeleton": original_code}

            try:
                print(f"发送到 OpenRouter. URL: {api_url}, 模型: {request_data['model']}")
                
                response = requests.post(api_url, headers=request_headers, data=json.dumps(request_data), timeout=timeout)
                response.raise_for_status() 

                response_content_text = response.text 
                response_json = response.json() 
                
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    message_content = response_json['choices'][0].get('message', {}).get('content')
                    if message_content:
                        raw_llm_output_json_str = message_content 
                    else:
                        raise KeyError("LLM响应缺少 'content' 字段 (在 choices[0].message 中)")
                else:
                    raise KeyError("LLM响应缺少 'choices' 字段或 'choices' 为空。")

                cleaned_json_str = raw_llm_output_json_str.strip()
                if cleaned_json_str.startswith("```json"):
                    cleaned_json_str = cleaned_json_str[len("```json"):].lstrip()
                elif cleaned_json_str.startswith("```"):
                    cleaned_json_str = cleaned_json_str[len("```"):].lstrip()
                if cleaned_json_str.endswith("```"):
                    cleaned_json_str = cleaned_json_str[:-len("```")].rstrip()
                
                llm_response_data = json.loads(cleaned_json_str)

                print("\nDEBUG: 解析后的LLM响应数据 (llm_response_data):")
                print(json.dumps(llm_response_data, indent=2, ensure_ascii=False))
                print("---------------------------------------------------\n")

            except requests.exceptions.HTTPError as e_http:
                print(f"Python API: OpenRouter API请求失败 (HTTPError): {e_http}")
                print(f"响应内容: {e_http.response.text if e_http.response else 'N/A'}")
                return {"status": "error", "message": f"LLM API请求失败: {str(e_http)}", "active_module_definitions": [], "html_skeleton": original_code}
            except requests.exceptions.RequestException as e_req:
                print(f"Python API: OpenRouter API请求失败: {e_req}")
                return {"status": "error", "message": f"LLM API请求失败: {str(e_req)}", "active_module_definitions": [], "html_skeleton": original_code}
            except json.JSONDecodeError as e_json: 
                problematic_string = cleaned_json_str if cleaned_json_str is not None else (response_content_text if 'response_content_text' in locals() else "N/A")
                print(f"Python API: 解析JSON时出错: {e_json}")
                print(f"导致JSON解析错误的原始文本: {problematic_string}")
                return {"status": "error", "message": f"返回的JSON格式无效: {str(e_json)}", "active_module_definitions": [], "html_skeleton": original_code}
            except KeyError as e_key:
                response_json_for_error = response_json if 'response_json' in locals() else "N/A"
                print(f"Python API: LLM返回的JSON缺少关键字段: {e_key}")
                print(f"LLM返回的JSON对象 (导致KeyError的): {json.dumps(response_json_for_error, indent=2, ensure_ascii=False) if isinstance(response_json_for_error, dict) else response_json_for_error}")
                return {"status": "error", "message": f"LLM返回的JSON缺少字段: {str(e_key)}", "active_module_definitions": [], "html_skeleton": original_code}
            except Exception as e_exc:
                print(f"Python API: LLM分析过程中发生未知错误: {e_exc}")
                return {"status": "error", "message": f"LLM分析时发生未知错误: {str(e_exc)}", "active_module_definitions": [], "html_skeleton": original_code}

        if not llm_response_data or "definitions" not in llm_response_data:
            print("错误: LLM响应数据不完整或格式不正确 (llm_response_data is None or 'definitions' not in it)。")
            return {"status": "error", "message": "LLM响应数据不完整或格式不正确。", "active_module_definitions": [], "html_skeleton": original_code}

        all_defs = llm_response_data.get("definitions", [])
        suggested_count = llm_response_data.get("module_count_suggestion", 0)
        max_allowed_from_config = self.api_config.get("max_modules_to_process_frontend", 10)
        num_to_process = min(suggested_count, max_allowed_from_config, len(all_defs))
        current_active_module_definitions = all_defs[:num_to_process]

        processed_active_definitions = []
        print("\n--- 开始处理模块定义 ---")
        for module_def in current_active_module_definitions:
            llm_start_comment_text = module_def.get('start_comment','').strip()
            llm_end_comment_text = module_def.get('end_comment','').strip()
            
            # --- 关键修正 v9: 在日志中也正确构建实际的HTML注释标记 ---
            actual_start_marker = f"" # 更正！
            actual_end_marker = f""   # 更正！
            # --- 结束关键修正 v9 ---
            
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def)
            
            print(f"DEBUG: 模块ID '{module_def.get('id')}':")
            print(f"  LLM 起始注释文本: '{llm_start_comment_text}' -> Python 构建的起始标记: '{actual_start_marker}'")
            print(f"  LLM 结束注释文本:   '{llm_end_comment_text}' -> Python 构建的结束标记: '{actual_end_marker}'")
            if not content:
                 print(f"  警告: original_content 为空。请检查输入HTML中是否存在标记 '{actual_start_marker}' 和 '{actual_end_marker}' 并正确界定内容。")
            print(f"  提取到的 original_content (前100字符): '{content[:100]}...' (长度: {len(content)})")
            processed_active_definitions.append({**module_def, "original_content": content})
        print("--- 结束处理模块定义 ---\n")


        skeleton = self._generate_skeleton_from_string(self.original_html_content_py, current_active_module_definitions)

        print("\nDEBUG: 处理后的活动模块定义 (将发送到前端):")
        print(json.dumps(processed_active_definitions, indent=2, ensure_ascii=False))
        print("---------------------------------------------------\n")


        print("\nDEBUG: 生成的HTML骨架 (将发送到前端):")
        print(skeleton)
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
            return {"status": "error", "message": "无效的JSON (modified_modules)", "final_html": skeleton_html}

        final_html = skeleton_html
        for module_id, new_content in modified_modules.items():
            # --- 关键修正 v9: 精确重建占位符 ---
            placeholder = f"" # 更正！
            # --- 结束关键修正 v9 ---
            final_html = final_html.replace(placeholder, str(new_content if new_content is not None else ""))
        
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
