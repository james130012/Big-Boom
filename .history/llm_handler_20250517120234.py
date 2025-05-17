# llm_handler.py
import requests
import json
import logging
import os

# 从 main.py 移动过来，如果变化更多，可以进一步参数化或管理。
PROMPT_TEMPLATE_BASE_MODIFICATION = """你是一个专业的Web前端开发助手。你的任务是帮助用户修改HTML网页的指定部分（如动画、样式、文本等），实现用户指定的功能，确保不影响其他组件（其他动画、文本、布局）。网页用于论文解读，包含HTML5、CSS、JavaScript和MathJax公式。

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
"""

PROMPT_TEMPLATE_DEFINITION = """请分析以下HTML代码，识别其中主要的、功能独立的模块区域。
对于每个识别出的模块，请提供以下信息，并严格按照JSON格式返回。JSON对象应包含一个名为 "definitions" 的键，其值为模块定义数组。
模块定义应包含：
- "id": "<模块的唯一ID，小写蛇形命名法，例如 'main_content_area', 'figure_1_section', 'contact_form'>"
- "description": "<模块的中文描述，例如 '主要内容区域，包含文章和侧边栏', '图1及其说明文字的整个容器', '用户联系表单'>"
- "start_char": <模块在原始HTML中的起始字符索引 (0-based)>
- "end_char": <模块在原始HTML中的结束字符索引 (0-based, exclusive)>
- "start_comment": "LLM_MODULE_START: <ID>" (请使用你生成的ID，确保ID与"id"字段完全一致)
- "end_comment": "LLM_MODULE_END: <ID>" (请使用你生成的ID，确保ID与"id"字段完全一致)

重点识别那些用户可能希望作为一个整体进行修改或引用的部分，例如：
- 包含标题和相关段落的整个 `<section>` 或 `<article>`。
- 具有明确ID或主要功能性类名的 `<div>` 容器及其全部内容。
- 与特定图表、图像或交互元素相关的完整区块（例如，包含 `<canvas>` 和控制按钮的父 `div`）。
- 整个页眉 (`<header>`)、页脚 (`<footer>`)、导航栏 (`<nav>`)。
- 避免将单个 `<p>` 标签或非常小的 `<span>` 元素识别为独立模块，除非它们本身具有非常特殊且独立的功能。
- **确保 `start_char` 和 `end_char` 精确包围模块的完整内容，不包括外部标签的开始或结束部分，除非该外部标签本身就是模块的根。**
- **`start_comment` 和 `end_comment` 中的 `<ID>` 必须与该模块定义的 `id` 字段的值完全匹配。**

HTML代码：
{raw_html_code}

JSON输出（确保包含 "definitions" 键，并且 "start_char", "end_char" 精确包围模块内容，"start_comment" 和 "end_comment" 中的ID与模块"id"一致）：
"""


class LLMHandler:
    def __init__(self, api_config, openrouter_api_key, site_url, site_name):
        self.api_config = api_config
        self.openrouter_api_key = openrouter_api_key
        self.site_url = site_url
        self.site_name = site_name
        if not self.openrouter_api_key:
            logging.warning("OPENROUTER_API_KEY 未设置。LLM 调用将被跳过/模拟。")

    def _call_llm_api(self, prompt_content, is_json_object_response=True):
        if not self.openrouter_api_key:
            # 这个模拟响应应与预期结构一致
            logging.warning("由于未设置 API 密钥，跳过实际的 LLM 调用。")
            if "definitions" in prompt_content.lower() : # 粗略检查是否为定义提示
                 return {"status": "success_mock", "message": "模拟的 LLM 定义响应。", "data": {"definitions": [
                    {"id": "mock_header", "description": "模拟页眉区域", "start_char": 0, "end_char": 20, "start_comment": "LLM_MODULE_START: mock_header", "end_comment": "LLM_MODULE_END: mock_header"},
                    {"id": "mock_content", "description": "模拟内容区域", "start_char": 21, "end_char": 40, "start_comment": "LLM_MODULE_START: mock_content", "end_comment": "LLM_MODULE_END: mock_content"}
                 ]}}
            else: # 假设是修改提示
                return {"status": "success_mock", "message": "模拟的 LLM 修改响应。", "data": {
                    "status": "success",
                    "message": "模拟修改完成。",
                    "modules": [{"id":"mock_target_module", "description":"一个被模拟指令针对的模块"}],
                    "modification_manual": "模拟手册：1. 这样做。2. 那样做。",
                    "modified_code": {"html": "<p>模拟的HTML</p>", "css": "", "js": ""}
                }}

        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url, # 可选，但建议设置
            "X-Title": self.site_name      # 可选，但建议设置
        }
        payload = {
            "model": self.api_config.get("default_model"),
            "messages": [{"role": "user", "content": prompt_content}],
            "temperature": self.api_config.get("llm_temperature"),
            "max_tokens": self.api_config.get("llm_max_tokens")
        }
        if is_json_object_response:
            payload["response_format"] = {"type": "json_object"}

        try:
            logging.info(f"调用 LLM API: {self.api_config.get('api_url')} 使用模型 {payload['model']}")
            response = requests.post(
                self.api_config.get("api_url"),
                headers=headers,
                json=payload,
                timeout=self.api_config.get("request_timeout_seconds")
            )
            response.raise_for_status() # 对于错误的响应 (4XX 或 5XX) 会引发 HTTPError
            
            raw_response_text = ""
            # 尝试获取内容，保持健壮性
            try:
                json_response = response.json()
                if json_response.get("choices") and len(json_response["choices"]) > 0:
                    message = json_response["choices"][0].get("message", {})
                    raw_response_text = message.get("content", "")
                else: # 如果结构不符合预期，则回退
                    logging.warning("LLM 响应 'choices' 结构不符合预期。使用完整的响应文本。")
                    raw_response_text = response.text
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logging.error(f"无法解析 LLM JSON 响应或访问内容: {e}。使用完整的响应文本。")
                raw_response_text = response.text

            logging.debug(f"LLM 原始响应 (前 1000 个字符): {raw_response_text[:1000]}")

            # 清理和解析 JSON
            cleaned_text = raw_response_text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[len("```json"):].strip()
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-len("```")].strip()
            
            if not cleaned_text:
                raise ValueError("LLM 在清理装饰器后返回了空内容。")

            parsed_json = json.loads(cleaned_text)
            return {"status": "success", "message": "LLM 调用成功。", "data": parsed_json}

        except requests.exceptions.RequestException as req_e:
            logging.error(f"LLM API RequestException: {req_e}")
            return {"status": "error", "message": f"LLM API 请求错误: {req_e}", "data": None}
        except json.JSONDecodeError as json_e:
            logging.error(f"解析 LLM 响应时发生 JSONDecodeError: {json_e}")
            logging.error(f"导致 JSON 解析问题的文本 (前 500 个字符): {cleaned_text[:500] if 'cleaned_text' in locals() else raw_response_text[:500]}")
            return {"status": "error", "message": f"LLM 响应不是有效的 JSON 格式: {json_e}", "data": None}
        except Exception as e:
            logging.error(f"LLM 调用或解析过程中发生意外错误: {e}")
            return {"status": "error", "message": f"意外的 LLM 错误: {e}", "data": None}

    def get_module_definitions(self, raw_original_code):
        """从 LLM 获取模块定义。"""
        prompt = PROMPT_TEMPLATE_DEFINITION.format(raw_html_code=raw_original_code)
        logging.info("正在从 LLM 请求模块定义。")
        
        response = self._call_llm_api(prompt)

        if response["status"] in ["success", "success_mock"] and response["data"]:
            if isinstance(response["data"], dict):
                definitions = response["data"].get("definitions", [])
                if not isinstance(definitions, list):
                    logging.error(f"LLM 'definitions' 不是列表: {type(definitions)}。数据: {response['data']}")
                    return {"status": "error", "message": "LLM 'definitions' 字段不是列表。", "definitions": []}
                logging.info(f"LLM 返回了 {len(definitions)} 个模块定义。")
                return {"status": "success", "message": response["message"], "definitions": definitions}
            else: # 如果 json_object 类型被遵守并且解析正确，则不应发生这种情况
                logging.error(f"LLM 定义响应数据不是字典: {type(response['data'])}。数据: {response['data']}")
                return {"status": "error", "message": "LLM 定义响应不是预期的 JSON 对象。", "definitions": []}

        logging.error(f"从 LLM 获取模块定义失败: {response['message']}")
        return {"status": "error", "message": response["message"], "definitions": []}


    def get_code_modification(self, raw_original_code, specific_instruction):
        """根据指令从 LLM 获取代码修改。"""
        if not specific_instruction:
            return {"status": "skipped", "message": "未提供具体指令。", "data": None}
        
        # 构造修改提示内容
        # 这种方法更好：在提示中直接包含 HTML。
        prompt_content_for_modification = f"""{PROMPT_TEMPLATE_BASE_MODIFICATION}

用户提供的HTML代码如下:
```html
{raw_original_code}
```

请根据以上HTML代码和之前的修改指令 ({specific_instruction}) 来执行任务。
"""
        logging.info(f"正在从 LLM 请求代码修改，指令为: {specific_instruction}")
        response = self._call_llm_api(prompt_content_for_modification) # 期望一个 JSON 对象

        if response["status"] in ["success", "success_mock"] and response["data"]:
            # 预期的响应结构直接是来自提示的 JSON。
            llm_output_data = response["data"]
            if llm_output_data.get("status") == "success":
                logging.info("LLM 修改成功。")
                return {
                    "status": "success",
                    "message": llm_output_data.get("message", "修改成功。"),
                    "modified_code": llm_output_data.get("modified_code", {}),
                    "modification_manual": llm_output_data.get("modification_manual", ""),
                    "affected_modules_by_llm": llm_output_data.get("modules", []) # LLM 可能会识别它认为已修改的模块
                }
            else:
                error_msg = llm_output_data.get('message', 'LLM 在修改过程中报告错误。')
                logging.error(f"LLM 修改失败: {error_msg}")
                return {"status": "error", "message": error_msg, "data": llm_output_data}
        
        logging.error(f"从 LLM 获取代码修改失败: {response['message']}")
        return {"status": "error", "message": response["message"], "data": response.get("data")}

    def get_prompt_template_for_frontend(self):
        """返回用于前端显示的基本修改提示模板。"""
        # 替换掉前端不需要看到或可能引起混淆的占位符。
        return PROMPT_TEMPLATE_BASE_MODIFICATION.replace("{user_html_code}", "[用户 HTML 将在此处提供给LLM]").replace("{specific_instruction}", "[用户修改指令将在此处提供给LLM]")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    # 示例用法 (需要设置 OPENROUTER_API_KEY 环境变量才能进行真实调用)
    from dotenv import load_dotenv
    load_dotenv() # 加载 .env 文件 (如果存在)

    mock_api_config = {
        "api_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "google/gemini-2.5-flash-preview", # "openai/gpt-3.5-turbo"
        "llm_temperature": 0.1,
        "llm_max_tokens": 4096,
        "request_timeout_seconds": 120
    }
    
    # 要使用实际 API 进行测试，请在环境中设置您的 OPENROUTER_API_KEY
    api_key = os.getenv("OPENROUTER_API_KEY") # 如果未设置，则为 None，将导致模拟响应
    
    handler = LLMHandler(
        api_config=mock_api_config,
        openrouter_api_key=api_key,
        site_url="http://localhost:8000/test-site", # 示例
        site_name="TestLLMHandlerApp"               # 示例
    )

    sample_html = """<!DOCTYPE html>
    <html>
    <head><title>测试页面</title></head>
    <body>
        <header id="header_main"><h1>主要标题</h1></header>
        <section id="content_area"><p>这里是一些内容。</p></section>
        <footer id="footer_info"><p>&copy; 2025</p></footer>
    </body>
    </html>"""

    print("\n--- 测试 get_module_definitions ---")
    definitions_result = handler.get_module_definitions(sample_html)
    print(json.dumps(definitions_result, indent=2, ensure_ascii=False)) # ensure_ascii=False 以正确显示中文
    assert definitions_result["status"] == "success" or definitions_result["status"] == "success_mock"
    if definitions_result["status"] == "success": # 或 success_mock
      assert "definitions" in definitions_result
      if not api_key: # 检查模拟数据结构
          assert len(definitions_result["definitions"]) > 0 
          assert definitions_result["definitions"][0]["id"].startswith("mock_")

    print("\n--- 测试 get_code_modification ---")
    instruction = "将主要标题更改为“新的超棒标题”，并使段落文本变为蓝色。"
    modification_result = handler.get_code_modification(sample_html, instruction)
    print(json.dumps(modification_result, indent=2, ensure_ascii=False))
    assert modification_result["status"] in ["success", "error", "success_mock"] # 如果 LLM 失败，则可能出现错误
    if not api_key: # 检查模拟数据结构
        assert modification_result["status"] == "success_mock"
        assert "modified_code" in modification_result
        assert modification_result["modified_code"]["html"] == "<p>模拟的HTML</p>"

    print("\n--- 测试 get_prompt_template_for_frontend ---")
    frontend_prompt = handler.get_prompt_template_for_frontend()
    # print(frontend_prompt) # 内容较长，仅检查其是否能运行
    assert "[用户 HTML 将在此处提供给LLM]" in frontend_prompt
    
    print("\nLLM Handler 测试完成。")
