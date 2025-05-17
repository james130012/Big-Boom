PS C:\Users\Administrator\Documents\bigboom\Big-Boom> & C:/Users/Administrator/AppData/Local/Programs/Python/Python312/python.exe c:/Users/Administrator/Documents/bigboom/Big-Boom/main.py
成功加载API配置文件: api_config.json
[pywebview] Using WinForms / Chromium
[pywebview] HTTP server root path: C:\Users\Administrator\Documents\bigboom\Big-Boom
Bottle v0.13.2 server starting up (using ThreadedAdapter())...
Listening on http://127.0.0.1:28504/
Hit Ctrl-C to quit.

127.0.0.1 - - [16/May/2025 21:56:29] "GET /gui.html HTTP/1.1" 200 13777
127.0.0.1 - - [16/May/2025 21:56:30] "GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1" 404 771
[pywebview] before_load event fired. injecting pywebview object
[pywebview] Loading JS files from C:\Users\Administrator\AppData\Local\Programs\Python\Python312\Lib\site-packages\webview\js
127.0.0.1 - - [16/May/2025 21:56:36] "GET /favicon.ico HTTP/1.1" 404 734
[pywebview] _pywebviewready event fired
[pywebview] loaded event fired
Python API: analyze_html 调用。
DEBUG: 在 analyze_html 中, API Key 是: SET
OpenRouter API密钥已加载。准备调用LLM (模型: google/gemini-2.5-flash-preview)...
发送到 OpenRouter. URL: https://openrouter.ai/api/v1/chat/completions, 模型: google/gemini-2.5-flash-preview

DEBUG: 解析后的LLM响应数据 (llm_response_data):
{
  "module_count_suggestion": 5,
  "definitions": [
    {
      "id": "header_module",
      "description": "页面顶部区域，包含网站Logo和标题。",
      "start_comment": "LLM_MODULE_START: header_module",
      "end_comment": "LLM_MODULE_END: header_module",
      "module_content_html": "<header><h1>网站Logo和标题</h1></header>"
    },
    {
      "id": "navigation_module",
      "description": "页面导航区域，包含主要链接。",
      "start_comment": "LLM_MODULE_START: navigation_module",
      "end_comment": "LLM_MODULE_END: navigation_module",
      "module_content_html": "<nav><ul><li>首页</li><li>产品</li><li>联系我们</li></ul></nav>"
    },
    {
      "id": "main_content_area",
      "description": "主要内容区域和侧边栏的容器。",
      "start_comment": "LLM_MODULE_START: main_content_area",
      "end_comment": "LLM_MODULE_END: main_content_area",
      "module_content_html": "<div class=\"main-area\">\n        <main>\n            <h2>主要文章区域</h2>\n            <p>这是一些主要内容...</p>\n            <p>段落二，包含<strong>加粗</strong>和<em>斜 体</em>。</p>\n        </main>\n        <aside style=\"float:right; width:200px; background:#eee; padding:10px;\"><h3>侧边栏</h3><p>广告或链接</p></aside>\n        </div>"
    },
    {
      "id": "main_article_module",
      "description": "页面的主要文章或内容块。",
      "start_comment": "LLM_MODULE_START: main_article_module",
      "end_comment": "LLM_MODULE_END: main_article_module",
      "module_content_html": "<main>\n            <h2>主要文章区域</h2>\n            <p>这是一些主要内容...</p>\n            <p>段落二，包含<strong>加粗</strong>和<em>斜体</em>。</p>\n        </main>"     
    },
    {
      "id": "sidebar_module",
      "description": "页面的侧边栏区域，通常包含辅助信息或广告。",
      "start_comment": "LLM_MODULE_START: sidebar_module",
      "end_comment": "LLM_MODULE_END: sidebar_module",
      "module_content_html": "<aside style=\"float:right; width:200px; background:#eee; padding:10px;\"><h3>侧边栏</h3><p>广告或链接</p></aside>"
    },
    {
      "id": "footer_module",
      "description": "页面底部区域，通常包含版权信息或联系方式。",
      "start_comment": "LLM_MODULE_START: footer_module",
      "end_comment": "LLM_MODULE_END: footer_module",
      "module_content_html": "<footer><p>版权所有 &copy; 2025</p></footer>"
    }
  ]
}
DEBUG: LLM处理后，带注释的HTML (前250字符): '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...'

--- 开始处理模块定义 (基于带注释的HTML) ---
DEBUG: 模块ID 'header_module':
  期望的起始标记: ''
  期望的结束标记: ''
  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...') 中是否存在标记并正确界定内容。
  提取到的 original_content (前100字符): '...' (长度: 0)
DEBUG: 模块ID 'navigation_module':
  期望的起始标记: ''
  期望的结束标记: ''
  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...') 中是否存在标记并正确界定内容。
  提取到的 original_content (前100字符): '...' (长度: 0)
DEBUG: 模块ID 'main_content_area':
  期望的起始标记: ''
  期望的结束标记: ''
  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...') 中是否存在标记并正确界定内容。
  提取到的 original_content (前100字符): '...' (长度: 0)
DEBUG: 模块ID 'main_article_module':
  期望的起始标记: ''
  期望的结束标记: ''
  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...') 中是否存在标记并正确界定内容。
  提取到的 original_content (前100字符): '...' (长度: 0)
DEBUG: 模块ID 'sidebar_module':
  期望的起始标记: ''
  期望的结束标记: ''
  警告: original_content 为空。检查 self.original_html_content_py (前250字符: '<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </st...') 中是否存在标记并正确界定内容。
  提取到的 original_content (前100字符): '...' (长度: 0)
--- 结束处理模块定义 ---


DEBUG: 处理后的活动模块定义 (将发送到前端):
[
  {
    "id": "header_module",
    "description": "页面顶部区域，包含网站Logo和标题。",
    "start_comment": "LLM_MODULE_START: header_module",
    "end_comment": "LLM_MODULE_END: header_module",
    "module_content_html": "<header><h1>网站Logo和标题</h1></header>",
    "original_content": ""
  },
  {
    "id": "navigation_module",
    "description": "页面导航区域，包含主要链接。",
    "start_comment": "LLM_MODULE_START: navigation_module",
    "end_comment": "LLM_MODULE_END: navigation_module",
    "module_content_html": "<nav><ul><li>首页</li><li>产品</li><li>联系我们</li></ul></nav>",
    "original_content": ""
  },
  {
    "id": "main_content_area",
    "description": "主要内容区域和侧边栏的容器。",
    "start_comment": "LLM_MODULE_START: main_content_area",
    "end_comment": "LLM_MODULE_END: main_content_area",
    "module_content_html": "<div class=\"main-area\">\n        <main>\n            <h2>主要文章区域</h2>\n            <p>这是一些主要内容...</p>\n            <p>段落二，包含<strong>加粗</strong>和<em>斜体</em>。</p>\n        </main>\n        <aside style=\"float:right; width:200px; background:#eee; padding:10px;\"><h3>侧边栏</h3><p>广告或链接</p></aside>\n        </div>",
    "original_content": ""
  },
  {
    "id": "main_article_module",
    "description": "页面的主要文章或内容块。",
    "start_comment": "LLM_MODULE_START: main_article_module",
    "end_comment": "LLM_MODULE_END: main_article_module",
    "module_content_html": "<main>\n            <h2>主要文章区域</h2>\n            <p>这是一些主要内容...</p>\n            <p>段落二，包含<strong>加粗</strong>和<em>斜体</em>。</p>\n        </main>",      
    "original_content": ""
  },
  {
    "id": "sidebar_module",
    "description": "页面的侧边栏区域，通常包含辅助信息或广告。",
    "start_comment": "LLM_MODULE_START: sidebar_module",
    "end_comment": "LLM_MODULE_END: sidebar_module",
    "module_content_html": "<aside style=\"float:right; width:200px; background:#eee; padding:10px;\"><h3>侧边栏</h3><p>广告或链接</p></aside>",
    "original_content": ""
  }
]
---------------------------------------------------


DEBUG: 生成的HTML骨架 (将发送到前端):
<!DOCTYPE html>
<html>
<head><title>示例页</title>
<style> body {font-family: sans-serif;} header, footer {padding: 1em; background-color: #f0f0f0; text-align: center;} nav ul {list-style: none; padding:0;} nav li {display: inline; margin: 0 10px;} </style>
</head>
<body>
    <header><h1>网站Logo和标题</h1></header>
    <nav><ul><li>首页</li><li>产品</li><li>联系我们</li></ul></nav>
    <div class="main-area">
        <main>
            <h2>主要文章区域</h2>
            <p>这是一些主要内容...</p>
            <p>段落二，包含<strong>加粗</strong>和<em>斜体</em>。</p>
        </main>
        <aside style="float:right; width:200px; background:#eee; padding:10px;"><h3>侧边栏</h3><p>广告或链接</p></aside>
        </div>
    <div style="clear:both;"></div>

    <footer><p>版权所有 &copy; 2025</p></footer>
    </body>
</html>
---------------------------------------------------
