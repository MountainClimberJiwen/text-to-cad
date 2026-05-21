import requests
import json

def generate_urs_hardware_scheme():
    # 1. 配置OpenAI兼容接口参数（根据实际接口修改）
    api_key = "your_openai_compatible_api_key"  # 替换为你的接口密钥
    api_base = "https://api.example.com/v1"      # 替换为你的兼容接口地址（如Azure OpenAI、本地化接口）
    model = "gpt-3.5-turbo"                     # 替换为接口支持的模型（如gpt-4、claude-3等兼容模型）
    
    # 2. 选中的Workflow内容作为提示词（核心提示，贴合目录精简版）
    prompt = """
你是URS硬件结构方案设计专家，需结合以下精简版工作流程，生成完整、详细的A1、A2自动注射笔URS硬件结构方案，方案需贴合流程每一个核心环节，逻辑连贯、细节详实，适配自动注射笔硬件结构需求。

核心工作流程（贴合目录精简版）：
1. 需求抽象与拆解：提炼硬件结构核心需求（尺寸、材质等），明确结构边界与约束
2. 方案框架与架构设计：规划设备物理布局，划分硬件功能模块及衔接逻辑
3. 模块级硬件结构细节设计：完成通用硬件模块设计，优化设备特性适配细节
4. 验证与交付：开展硬件安装、性能等相关验证，明确交付内容与周期

要求：方案需围绕A1、A2自动注射笔的硬件结构展开，覆盖上述所有流程环节，补充必要的硬件设计细节（如尺寸参数、材质选型、模块衔接方式、验证标准等），符合工业设备方案规范，可直接用于项目落地参考。
    """
    
    # 3. 构造接口请求参数（OpenAI兼容格式）
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt.strip()  # 去除多余空格，优化提示词格式
            }
        ],
        "temperature": 0.3,  # 控制生成内容的严谨性，越低越贴合提示词
        "max_tokens": 2000   # 根据方案长度需求调整，足够生成完整方案
    }
    
    try:
        # 4. 发送请求调用接口
        response = requests.post(
            url=f"{api_base}/chat/completions",
            headers=headers,
            data=json.dumps(payload)
        )
        response.raise_for_status()  # 抛出HTTP请求异常（如401密钥错误、404接口地址错误）
        
        # 5. 解析接口返回结果，提取生成的方案内容
        result = response.json()
        scheme_content = result["choices"][0]["message"]["content"].strip()
        
        # 6. 将生成的方案保存到本地文件（便于查看和使用）
        with open("A1A2_auto_injection_pen_URS_hardware_scheme.md", "w", encoding="utf-8") as f:
            f.write(scheme_content)
        
        print("方案生成成功！已保存至：A1A2_auto_injection_pen_URS_hardware_scheme.md")
        return scheme_content
    
    except Exception as e:
        print(f"方案生成失败，错误信息：{str(e)}")
        # 异常处理：返回错误提示，便于排查问题
        if "401" in str(e):
            print("提示：请检查接口密钥是否正确")
        elif "404" in str(e):
            print("提示：请检查接口地址是否正确")
        return None

# 执行函数，生成方案
if __name__ == "__main__":
    generated_scheme = generate_urs_hardware_scheme()
    # 可选：打印生成的方案内容（便于快速查看）
    if generated_scheme:
        print("\n生成的方案预览：")
        print("-" * 50)
        print(generated_scheme[:500] + "...")  # 预览前500字符

使用说明：

1. 替换代码中api_key、api_base为你的OpenAI兼容接口实际参数（如Azure OpenAI需配置对应endpoint和密钥）；

2. 根据接口支持的模型，修改model参数（如gpt-4、通义千问兼容版等）；

3. 运行代码后，生成的方案会自动保存为markdown文件，同时在控制台预览前500字符；

4. 若接口调用失败，控制台会输出具体错误提示，可根据提示排查密钥、接口地址等问题。
