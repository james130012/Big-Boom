import webview
import json
import os
import logging
import requests
import re
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Define the base template for LLM prompts
PROMPT_TEMPLATE_BASE = """你是一个专业的Web前端开发助手。你的任务是帮助用户修改HTML网页的指定部分（如动画、样式、文本等），实现用户指定的功能，确保不影响其他组件（其他动画、文本、布局）。网页用于论文解读，包含HTML5、CSS、JavaScript和MathJax公式。

**重要指令**：
1. 返回严格的JSON格式，遵循下方结构，所有字符串值用双引号。
2. 若输入HTML为空或无效，返回 {"status": "error", "message": "无效或空HTML", "modules": [], "modification_manual": "", "modified_code": {}}.
3. **任务详情**：
   - **输入**：用户提供HTML代码和修改指令（{specific_instruction}）。
   - **目标**：根据修改指令识别目标元素（如特定动画、样式、文本）并实现新功能。
   - **要求**：
     - 动态识别目标元素的HTML、CSS、JS及关联项（如按钮、父容器、依赖样式/脚本）。
     - 生成新代码（HTML、CSS、JS）实现用户指定的功能。
     - 提供分步修改说明书，明确替换位置（行号或上下文）、添加/删除代码。
     - 确保不影响其他组件（如其他动画、布局、全局样式）。
     - 若修改涉及MathJax公式（如动画4、8），确保渲染正常（如触发MathJax.typesetPromise）。
   - **输出内容**：
     - **模块**：目标元素的模块，包含：
       - id：唯一标识（如"animation_box_1"或"body_styles"）。
       - description：模块描述（中文，如“动画1模块”或“页面背景样式”）。
       - html：当前HTML（目标元素及其子元素）。
       - css：相关CSS类/选择器列表。
       - js：相关JS函数或脚本。
       - associated_elements：关联元素（如按钮、描述、父容器）。
       - dependencies：依赖项（如全局样式、脚本）。
     - **新代码**：实现新功能的代码，包含：
       - html：新HTML（替换目标元素）。
       - css：新CSS（添加/修改样式）。
       - js：新JS（替换/添加函数）。
       - associated_elements：更新的关联元素（如按钮、描述）。
     - **修改说明书**：分步指南，包含：
       - 替换HTML的位置（行号或上下文）。
       - 添加/删除CSS（具体样式）。
       - 替换/添加JS（具体函数）。
       - 更新关联元素（如按钮、描述）。
       - 确保其他组件不受影响的注意事项。
4. **模块识别**：
   - 根据{specific_instruction}定位目标元素（如`<div class="animation-box" id="anim1-box">`或`body`）。
   - 分析关联项：父容器（如`<div class="animation-container">`）、按钮（如`<button onclick="playAnim1()">`）、描述（如`<p>`）、依赖样式（如`.animation-box`）、脚本（如`playAnim1`）。
   - 不修改无关元素（如其他动画、`<h1>`、`<div class="container">`）。
5. **新代码生成**：
   - 根据{specific_instruction}生成新HTML、CSS、JS。
   - 保留必要接口（如动画的`id="anim1-box"`、JS函数名`playAnim1`）。
   - 使用特定选择器（如`#anim1-box .cube`）避免影响其他元素。
   - 确保新代码适配父容器和全局样式（如`.animation-box`的`min-height: 150px`）。
6. **修改说明书**：
   - 指明替换位置（如“替换第100-104行HTML”）。
   - 列出CSS添加/删除（如“删除`.brain-outline`，添加`.cube`”）。
   - 指明JS替换/添加（如“替换`playAnim1`”）。
   - 说明关联元素更新（如“替换按钮为`<button onclick="playAnim1()">改变颜色</button>`”）。
   - 强调隔离措施（如“使用`#anim1-cube`避免影响其他动画”）。
7. **约束**：
   - 确保新代码与现有结构兼容（如保留父容器结构）。
   - 避免修改全局样式（如`body`、`.container`）或无关脚本（如`playAnim2`），除非指令明确要求。
   - 若涉及MathJax，添加渲染代码（如`MathJax.typesetPromise(['#anim1-box'])`）。
8. **输出JSON结构**：
```json
{
  "status": "<success 或 error>",
  "message": "<简要状态消息>",
  "modules": [
    {
      "id": "<模块ID，如animation_box_1>",
      "description": "<模块中文描述>",
      "html": "<当前目标元素HTML>",
      "css": ["<相关CSS类/选择器>", "..."],
      "js": "<相关JS代码>",
      "associated_elements": {
        "button": "<按钮HTML，若无则空>",
        "description": "<描述<p> HTML，若无则空>",
        "parent_container": "<父容器HTML，若无则空>",
        "other": "<其他关联元素，若无则空>"
      },
      "dependencies": ["<依赖项，如.animation-box样式>"
    }
  ],
  "modification_manual": "<分步修改指南>",
  "modified_code": {
    "html": "<新HTML>",
    "css": "<新CSS>",
    "js": "<新JS>",
    "associated_elements": {
      "button": "<新按钮HTML，若无则空>",
      "description": "<新描述<p> HTML，若无则空>",
      "parent_container": "<新父容器HTML，若无则空>",
      "other": "<其他新关联元素，若无则空>"
    }
  }
}
```

DEFAULT_API_CONFIG = {
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "default_model": "google/gemini-2.5-flash-preview",
    "base_headers": {"Content-Type": "application/json"},
    "request_timeout_seconds": 120,
    "llm_temperature": 0.1,
    "llm_max_tokens": 4096,
    "max_modules_to_process_frontend": 10
}

class Api:
    def __init__(self):
        self.original_html_content_py = "" 
        self.html_skeleton = ""            
        self.api_config = self._load_api_config()
        self.site_url = os.getenv("YOUR_SITE_URL", "http://localhost:8003/default-app") 
        self.site_name = os.getenv("YOUR_SITE_NAME", "DefaultModularizerAppV3") 
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.modified_modules = {}  
        self.module_definitions = [] 

    def _load_api_config(self, config_path="api_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logging.info(f"Successfully loaded API config file: {config_path}")
                return {**DEFAULT_API_CONFIG, **config} 
        except FileNotFoundError:
            logging.warning(f"API config file '{config_path}' not found. Using default config.")
            return DEFAULT_API_CONFIG
        except json.JSONDecodeError:
            logging.warning(f"API config file '{config_path}' is malformed. Using default config.")
            return DEFAULT_API_CONFIG
        except Exception as e:
            logging.warning(f"Error loading API config file: {e}. Using default config.")
            return DEFAULT_API_CONFIG

    def _add_comments_to_html_revised(self, original_html, definitions_from_llm):
        if not definitions_from_llm:
            return original_html
        processed_defs = []
        original_lines = original_html.splitlines(keepends=True)
        for i, d_orig in enumerate(definitions_from_llm):
            d = d_orig.copy()
            module_id = d.get("id", f"unknown_module_{i}")
            start_comment_text = d.get("start_comment", "").strip() # e.g., "LLM_MODULE_START: module_id"
            end_comment_text = d.get("end_comment", "").strip()     # e.g., "LLM_MODULE_END: module_id"
            if not all([module_id, start_comment_text, end_comment_text]):
                logging.warning(f"Module '{module_id}' in _add_comments_to_html_revised: incomplete comment texts. Skipping.")
                continue
            
            s_char, e_char = d.get("start_char"), d.get("end_char")
            if s_char is None or e_char is None: 
                s_line, e_line = d.get("start_line"), d.get("end_line")
                if s_line is None or e_line is None or \
                   not (1 <= s_line <= len(original_lines) and 1 <= e_line <= len(original_lines) and s_line <= e_line):
                    logging.warning(f"Module '{module_id}' has invalid/missing line/char numbers. Skipping.")
                    continue
                s_char = sum(len(line) for line in original_lines[:s_line - 1])
                e_char = sum(len(line) for line in original_lines[:e_line])
            
            if not (0 <= s_char <= e_char <= len(original_html)):
                logging.warning(f"Module '{module_id}' invalid char positions ({s_char}-{e_char}) for HTML length {len(original_html)}. Skipping.")
                continue
            
            d["s_char_final"], d["e_char_final"] = s_char, e_char
            # Corrected: Define the exact HTML comment tags to be inserted
            d["start_marker_tag_full"] = f"\n"
            d["end_marker_tag_full"] = f"\n"
            processed_defs.append(d)
        
        processed_defs.sort(key=lambda x: x["s_char_final"])
        result_parts, current_pos_in_original = [], 0
        for defi in processed_defs:
            s_char, e_char = defi["s_char_final"], defi["e_char_final"]
            if s_char > current_pos_in_original: result_parts.append(original_html[current_pos_in_original:s_char])
            result_parts.append(defi["start_marker_tag_full"])
            result_parts.append(original_html[s_char:e_char]) # This is the module's original content
            result_parts.append(defi["end_marker_tag_full"])
            current_pos_in_original = e_char
        
        if current_pos_in_original < len(original_html): result_parts.append(original_html[current_pos_in_original:])
        final_html = "".join(result_parts)
        logging.debug(f"_add_comments_to_html_revised output (first 300 chars): {final_html[:300]}...")
        return final_html

    def _extract_module_content_from_string(self, html_string_with_llm_comments, module_def):
        module_id = module_def.get('id', 'N/A')
        start_comment_text = module_def.get('start_comment', '').strip() 
        end_comment_text = module_def.get('end_comment', '').strip()
        if not start_comment_text or not end_comment_text: 
            logging.warning(f"Module '{module_id}' missing comment texts for extraction.")
            return None # Indicate failure

        # Corrected: Construct the full comment tags as they were inserted
        effective_start_marker = f"\n"
        effective_end_marker_prefix = f"\n" 

        start_idx = html_string_with_llm_comments.find(effective_start_marker)
        if start_idx == -1: 
            logging.warning(f"Start marker for '{module_id}' not found during extraction. Marker: '{effective_start_marker.strip()}'")
            return None 
        
        content_start_idx = start_idx + len(effective_start_marker)
        content_end_idx = html_string_with_llm_comments.find(effective_end_marker_prefix, content_start_idx)
        if content_end_idx == -1: 
            logging.warning(f"End marker for '{module_id}' not found during extraction. Marker prefix: '{effective_end_marker_prefix.strip()}'")
            return None 
        
        return html_string_with_llm_comments[content_start_idx:content_end_idx]

    def _generate_skeleton_from_string(self, html_string_with_llm_comments, modules_to_skeletonize):
        skeleton = html_string_with_llm_comments
        temp_modules = []
        for m_def in modules_to_skeletonize:
            m_copy = m_def.copy()
            if "s_char_final" not in m_copy: m_copy["s_char_final"] = m_copy.get("start_char", 0) # Fallback
            temp_modules.append(m_copy)
        
        sorted_modules = sorted(temp_modules, key=lambda x: x.get("s_char_final", 0), reverse=True)
        
        for module_def in sorted_modules:
            module_id = module_def.get('id', '').strip()
            start_comment_text = module_def.get('start_comment', '').strip()
            end_comment_text = module_def.get('end_comment', '').strip()
            if not module_id or not start_comment_text or not end_comment_text: continue

            # Corrected: These are the full comment tags as inserted by _add_comments_to_html_revised
            full_start_marker = f"\n"
            full_end_marker = f"\n"
            # Corrected: This is the placeholder for the skeleton
            placeholder = f"" 
            
            start_idx = skeleton.find(full_start_marker)
            if start_idx == -1: 
                logging.warning(f"Full start marker for '{module_id}' not found in skeleton generation.")
                continue
            
            end_idx_of_end_marker = skeleton.find(full_end_marker, start_idx + len(full_start_marker))
            if end_idx_of_end_marker == -1: 
                logging.warning(f"Full end marker for '{module_id}' not found in skeleton generation.")
                continue
            
            block_start, block_end = start_idx, end_idx_of_end_marker + len(full_end_marker)
            skeleton = skeleton[:block_start] + placeholder + skeleton[block_end:]
            logging.debug(f"Replaced module block for '{module_id}' with placeholder in skeleton.")
        return skeleton

    def analyze_html(self, original_code, specific_instruction=""):
        logging.info("Python API: analyze_html called.")
        raw_original_code = original_code.strip() if original_code else ""
        if not raw_original_code:
            return {"status": "error", "message": "无效或空HTML", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}

        definition_prompt = f"""分析以下HTML代码，严格按照JSON格式返回模块定义列表。每个模块包含：
"id": "<唯一ID>", "description": "<中文描述>", "start_char": <起始字符索引>, "end_char": <结束字符索引>, "start_comment": "LLM_MODULE_START: <ID>", "end_comment": "LLM_MODULE_END: <ID>"
HTML代码：
```html
{raw_original_code}
```
JSON输出：
"""
        raw_definitions_from_llm = []
        if not self.openrouter_api_key:
            logging.warning("OPENROUTER_API_KEY not set. Using mock data for definitions.")
            mock_defs = [ # Ensure these char numbers are accurate for your default HTML if testing mock
                {"id": "header_section", "description": "网站Logo和主要标题", "start_char": 500, "end_char": 556, "start_comment": "LLM_MODULE_START: header_section", "end_comment": "LLM_MODULE_END: header_section"},
                {"id": "anim1_box", "description": "动画1的容器", "start_char": 800, "end_char": 864, "start_comment": "LLM_MODULE_START: anim1_box", "end_comment": "LLM_MODULE_END: anim1_box"},
            ]
            raw_definitions_from_llm = mock_defs
        else:
            try:
                logging.info("Calling LLM for module definitions...")
                headers = {"Authorization": f"Bearer {self.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": self.site_url, "X-Title": self.site_name}
                payload = {"model": self.api_config.get("default_model"), "messages": [{"role": "user", "content": definition_prompt}], "temperature": 0.05, "max_tokens": self.api_config.get("llm_max_tokens", 4096), "response_format": {"type": "json_object"}}
                response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                response.raise_for_status()
                raw_llm_def_text = response.json()["choices"][0]["message"]["content"]
                logging.debug(f"LLM RAW DEFINITION RESPONSE TEXT: {raw_llm_def_text}")
                cleaned_def_text = raw_llm_def_text.strip("```json").strip("```").strip()
                if not cleaned_def_text: raise ValueError("LLM returned empty content for definitions.")
                llm_response_data = json.loads(cleaned_def_text)
                raw_definitions_from_llm = llm_response_data.get("definitions", [])
                logging.info(f"LLM returned {len(raw_definitions_from_llm)} module definitions.")
            except Exception as e:
                logging.error(f"Error during LLM call for definitions or parsing: {e}")
                return {"status": "error", "message": f"LLM API/Parse Error (Definitions): {e}", "active_module_definitions": [], "html_skeleton": "", "modified_code": {}, "modification_manual": ""}

        self.original_html_content_py = self._add_comments_to_html_revised(raw_original_code, raw_definitions_from_llm)
        
        temp_processed_definitions = []
        for module_def_llm in raw_definitions_from_llm:
            content = self._extract_module_content_from_string(self.original_html_content_py, module_def_llm)
            if content is not None: 
                temp_processed_definitions.append({**module_def_llm, "original_content": content.strip()})
            else:
                logging.warning(f"Could not extract original content for module ID: {module_def_llm.get('id')}. It will be excluded.")
        
        self.module_definitions = temp_processed_definitions
        logging.info(f"Processed {len(self.module_definitions)} modules with their original content.")

        self.html_skeleton = self._generate_skeleton_from_string(self.original_html_content_py, self.module_definitions)
        
        modified_code_for_response = {}
        modification_manual_for_response = ""
        self.modified_modules = {} 

        if specific_instruction:
            logging.info(f"Processing specific instruction: {specific_instruction}")
            modification_prompt = PROMPT_TEMPLATE_BASE.replace("{user_html_code}", raw_original_code).replace("{specific_instruction}", specific_instruction)
            
            if not self.openrouter_api_key:
                logging.warning("OPENROUTER_API_KEY not set. Skipping LLM call for modification.")
                modification_manual_for_response = "无API密钥，跳过LLM修改。"
            else:
                try:
                    logging.info("Calling LLM for code modification...")
                    headers = {"Authorization": f"Bearer {self.openrouter_api_key}", "Content-Type": "application/json", "HTTP-Referer": self.site_url, "X-Title": self.site_name}
                    payload = {"model": self.api_config.get("default_model"), "messages": [{"role": "user", "content": modification_prompt}], "temperature": self.api_config.get("llm_temperature", 0.1), "max_tokens": self.api_config.get("llm_max_tokens", 4096), "response_format": {"type": "json_object"}}
                    response = requests.post(self.api_config.get("api_url"), headers=headers, json=payload, timeout=self.api_config.get("request_timeout_seconds", 120))
                    response.raise_for_status()
                    
                    raw_llm_mod_text = ""
                    # Corrected try-except for Python syntax (no curly braces)
                    try:
                        if response.json().get("choices") and len(response.json()["choices"]) > 0:
                             raw_llm_mod_text = response.json()["choices"][0].get("message", {}).get("content", "")
                        else:
                            logging.error("LLM modification response has no 'choices' or 'choices' is empty.")
                            raw_llm_mod_text = response.text # Fallback
                    except (KeyError, AttributeError, ValueError, json.JSONDecodeError) as ke: 
                        logging.error(f"Error accessing LLM modification response content or response.json() failed: {ke}. Full response text (first 500 chars): {response.text[:500]}")
                        raw_llm_mod_text = response.text 

                    logging.info(f"LLM RAW MODIFICATION RESPONSE TEXT: {raw_llm_mod_text[:1000]}...")

                    llm_modification_response = {}
                    cleaned_mod_text = raw_llm_mod_text.strip("```json").strip("```").strip()
                    if not cleaned_mod_text:
                        logging.error("LLM modification response content is empty after stripping decorators.")
                        llm_modification_response = {"status": "error", "message": "LLM返回的修改内容为空。"}
                    else:
                        try:
                            llm_modification_response = json.loads(cleaned_mod_text)
                        except json.JSONDecodeError as json_e:
                            logging.error(f"Failed to parse LLM modification response as JSON: {json_e}")
                            logging.error(f"Problematic text for JSON parsing: {cleaned_mod_text[:500]}...")
                            llm_modification_response = {"status": "error", "message": f"LLM返回的修改内容不是有效的JSON格式: {json_e}"}

                    if llm_modification_response.get("status") == "success":
                        modified_code_for_response = llm_modification_response.get("modified_code", {})
                        modification_manual_for_response = llm_modification_response.get("modification_manual", "")
                        llm_rep_mods = llm_modification_response.get("modules", [])
                        if llm_rep_mods and isinstance(llm_rep_mods, list) and len(llm_rep_mods) > 0:
                            target_id = llm_rep_mods[0].get("id")
                            if target_id: self.modified_modules[target_id] = {"modified_code": modified_code_for_response, "modification_manual": modification_manual_for_response}
                    else:
                        logging.error(f"LLM reported error during modification: {llm_modification_response.get('message', 'Unknown LLM error')}")
                        modification_manual_for_response = f"LLM修改失败: {llm_modification_response.get('message', 'Unknown LLM error')}"
                except requests.exceptions.RequestException as req_e:
                    logging.error(f"HTTP Request Error (Modification): {req_e}")
                    modification_manual_for_response = f"LLM API请求错误 (修改): {req_e}"
                except Exception as e:
                    logging.error(f"Unexpected error (Modification): {e}")
                    modification_manual_for_response = f"处理LLM修改时发生意外错误: {e}"
        
        return {
            "status": "success", 
            "message": f"分析完成，识别到 {len(self.module_definitions)} 个模块。",
            "active_module_definitions": self.module_definitions[:self.api_config.get("max_modules_to_process_frontend")], 
            "html_skeleton": self.html_skeleton,
            "modified_code": modified_code_for_response, 
            "modification_manual": modification_manual_for_response
        }

    def integrate_modules_with_user_edits(self, user_edited_modules_json_string="{}"):
        logging.info("Python API: integrate_modules_with_user_edits called.")
        user_edited_modules_dict = {}
        try:
            if user_edited_modules_json_string: user_edited_modules_dict = json.loads(user_edited_modules_json_string)
        except json.JSONDecodeError as e: logging.error(f"Error parsing user_edited_modules_json_string: {e}")

        if not self.html_skeleton: return getattr(self, 'original_html_content_py', "错误：HTML骨架未生成。")
        final_html, all_modified_css, all_modified_js = self.html_skeleton, [], []

        for module_def in self.module_definitions:
            module_id = module_def.get("id")
            if not module_id: continue
            # Corrected placeholder to match what _generate_skeleton_from_string creates
            placeholder = f""
            content_to_insert, source = "", "original"
            
            if module_id in user_edited_modules_dict:
                content_to_insert = user_edited_modules_dict[module_id].get("html", "")
                source = "user_edit"
            elif module_id in self.modified_modules:
                llm_mod_data = self.modified_modules[module_id]["modified_code"]
                content_to_insert = llm_mod_data.get("html", "")
                if llm_mod_data.get("css"): all_modified_css.append(f"/* Module: {module_id} (LLM) */\n{llm_mod_data['css']}")
                if llm_mod_data.get("js"): all_modified_js.append(f"// Module: {module_id} (LLM)\n{llm_mod_data['js']}")
                source = "llm_edit"
            else:
                content_to_insert = module_def.get("original_content", "")
            
            if placeholder in final_html:
                final_html = final_html.replace(placeholder, content_to_insert, 1)
                logging.debug(f"Replaced '{module_id}' using {source} content.")
            else: 
                logging.warning(f"Placeholder '{placeholder}' for '{module_id}' not found in skeleton.")
        
        if all_modified_css:
            css_block = "\n<style type=\"text/css\">\n" + "\n\n".join(all_modified_css) + "\n</style>\n"
            if "</head>" in final_html: final_html = final_html.replace("</head>", css_block + "</head>", 1)
            else: final_html = css_block + final_html
        if all_modified_js:
            js_block = "\n<script type=\"text/javascript\">\n//<![CDATA[\n" + "\n\n".join(all_modified_js) + "\n//]]>\n</script>\n"
            if "</body>" in final_html: final_html = final_html.replace("</body>", js_block + "</body>", 1)
            else: final_html += js_block
        return final_html

    def get_prompt_template_for_frontend(self):
        return PROMPT_TEMPLATE_BASE.replace("{user_html_code}", "[用户 HTML 在此]").replace("{specific_instruction}", "[修改指令在此]")

if __name__ == '__main__':
    api = Api()
    webview.create_window('代码智能装配流水线', 'gui.html', js_api=api, width=1300, height=900, resizable=True)
    webview.start(debug=True)
