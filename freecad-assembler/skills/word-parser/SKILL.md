---
name: word-parser
description: Word 文档解析与需求提取 skill。用于消费后端已解析的 docx 文本，将用户上传文档内容转成结构化需求输入。
triggers:
  - word
  - docx
  - 文档
  - word解析
  - 需求提取
---

# Word Parser Skill

使用规则：

1. 仅使用后端已解析出的文档文本，不直接访问原始文件。
2. 先抽取用户需求约束、目标、边界与验收条件。
3. 再将提取结果与 URS-MANUAL 模块对齐，输出对应模块结论。
4. 若文档信息不足且 URS-MANUAL 无法支撑，返回：这个问题我还回答不了。

输出偏好：
- 先给结论，再给对应模块路径
- 不编造文档中不存在的参数
