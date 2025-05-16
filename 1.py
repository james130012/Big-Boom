import os
import json
import requests
from dotenv import load_dotenv

# 默认配置 (可以被 api_config.json 文件覆盖)
DEFAULT_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# 您可以尝试不同的模型，例如 "mistralai/mistral-7b-instruct:free" 或您在 api_config.json 中指定的模型
DEFAULT_MODEL = "google/gemini-2.5-flash-preview" 

def load_app_config(config_path="api_config.json"):
    """从JSON文件加载API配置"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"提示: 配置文件 '{config_path}' 未找到。将对URL和模型使用默认值。")
        return {}
    except json.JSONDecodeError:
        print(f"错误: 无法从 '{config_path}'解码JSON。将使用默认值。")
        return {}
    except Exception as e:
        print(f"错误: 加载配置文件 '{config_path}' 时发生未知错误: {e}。将使用默认值。")
        return {}


def test_llm_call(api_key, api_url, model, site_url=None, site_name=None):
    """执行对LLM API的测试调用"""
    if not api_key:
        print("错误: OPENROUTER_API_KEY 未设置。请在您的 .env 文件中设置它。")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # 如果提供了 site_url 和 site_name，则添加它们，与主应用程序类似
    # OpenRouter 的一些免费模型可能需要这些头信息
    if site_url:
        headers["HTTP-Referer"] = site_url
    if site_name:
        headers["X-Title"] = site_name
    
    # 一个非常简单的提示
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello, who are you? Respond in English."} 
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }

    print(f"\n正在尝试调用 LLM API...")
    print(f"URL: {api_url}")
    print(f"模型: {model}")
    # 打印所有将要发送的头信息，除了Authorization以保护密钥
    headers_to_print = {k: v for k, v in headers.items() if k.lower() != "authorization"}
    print(f"头信息 (部分): {json.dumps(headers_to_print, indent=2)}")
    print(f"数据: {json.dumps(data, indent=2)}")

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=60) # 使用 json=data 直接发送json格式数据
        
        print(f"\n响应状态码: {response.status_code}")
        print("响应头信息:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")

        print("\n响应体 (原始文本):")
        print(response.text)

        if response.status_code == 200:
            try:
                response_json = response.json()
                print("\n响应体 (解析后的JSON):")
                print(json.dumps(response_json, indent=2, ensure_ascii=False))

                if "choices" in response_json and len(response_json["choices"]) > 0:
                    message = response_json["choices"][0].get("message", {})
                    message_content = message.get("content")
                    if message_content:
                        print("\nLLM 消息内容:")
                        print(message_content)
                        print("\n成功: LLM 调用似乎工作正常并返回了内容。")
                    else:
                        print("\n警告: LLM 调用成功，但在预期位置未找到消息内容。")
                else:
                    print("\n警告: LLM 调用成功，但响应中缺少 'choices' 数组或该数组为空。")
            except json.JSONDecodeError:
                print("\n错误: 即使状态码为200，也未能将LLM响应解析为JSON。")
        else:
            print(f"\n错误: LLM API 调用失败，状态码为 {response.status_code}。")
            print("这可能是由于API密钥无效、模型名称不正确、网络问题或API提供商的问题。")
            print("请检查OpenRouter的错误代码含义。")

    except requests.exceptions.Timeout:
        print("\n错误: 请求LLM API超时。")
    except requests.exceptions.RequestException as e:
        print(f"\n错误: LLM API 请求过程中发生错误: {e}")

if __name__ == "__main__":
    # 从 .env 文件加载环境变量
    load_dotenv()
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    your_site_url = os.getenv("YOUR_SITE_URL", "http://localhost/llm-test") 
    your_site_name = os.getenv("YOUR_SITE_NAME", "LLMTestApp")

    # 从 api_config.json 加载配置
    app_config = load_app_config() # 默认从 "api_config.json" 加载
    
    api_url_to_use = app_config.get("api_url", DEFAULT_API_URL)
    model_to_use = app_config.get("default_model", DEFAULT_MODEL)
    
    if not openrouter_api_key:
        print("严重错误: 在 .env 文件中未找到 OPENROUTER_API_KEY。")
        print("请在该脚本所在目录下创建一个 .env 文件，内容如下:")
        print("OPENROUTER_API_KEY='your_actual_api_key_here'")
        print("YOUR_SITE_URL='https://your-registered-site.com' # (可选, 但推荐)")
        print("YOUR_SITE_NAME='Your Registered App Name' # (可选, 但推荐)")
    else:
        test_llm_call(openrouter_api_key, api_url_to_use, model_to_use, site_url=your_site_url, site_name=your_site_name)
