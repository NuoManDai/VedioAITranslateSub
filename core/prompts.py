import json
from core.utils import *


## ================================================================
# @ step4_splitbymeaning.py
def get_split_prompt(sentence, num_parts=2, word_limit=20):
    # 如果用户指定了语言则使用，否则使用检测到的语言
    user_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language")
    language = (
        user_language
        if user_language and user_language != "auto"
        else detected_language
    )
    language = get_language_name(language)  # 将语言代码转换为完整名称供LLM使用
    split_prompt = f"""
## 角色
你是一名专业的 Netflix 字幕分割专家，精通 **{language}** 语言。

## 任务
将给定的字幕文本分割成 **{num_parts}** 个部分，每部分少于 **{word_limit}** 个词。

1. 根据 Netflix 字幕标准保持句子语义连贯性
2. 最重要：保持各部分长度大致相等（每部分最少3个词）
3. 在标点符号或连词等自然断点处分割
4. 如果提供的文本是重复的词语，直接在重复词语的中间位置分割

## 步骤
1. 分析句子结构、复杂度和关键分割难点
2. 使用 [br] 标签在分割位置生成两种备选分割方案
3. 比较两种方案，突出各自的优缺点
4. 选择最佳分割方案

## 待分割文本
<split_this_sentence>
{sentence}
</split_this_sentence>

## 仅以 JSON 格式输出，不要添加其他文本
```json
{{
    "analysis": "简要描述句子结构、复杂度和关键分割难点",
    "split1": "第一种分割方案，在分割位置使用 [br] 标签",
    "split2": "备选分割方案，在分割位置使用 [br] 标签",
    "assess": "比较两种方案，突出各自的优缺点",
    "choice": "1 或 2"
}}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
""".strip()
    return split_prompt


"""{{
    "analysis": "对文本结构的简要分析",
    "split": "完整句子，在分割位置使用 [br] 标签"
}}"""


## ================================================================
# @ step4_1_summarize.py
def get_summary_prompt(source_content, custom_terms_json=None):
    # 如果用户指定了语言则使用，否则使用检测到的语言
    user_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language")
    src_lang = (
        user_language
        if user_language and user_language != "auto"
        else detected_language
    )
    src_lang = get_language_name(src_lang)  # 将语言代码转换为完整名称供LLM使用
    tgt_lang = load_key("target_language")

    # 添加自定义术语说明
    terms_note = ""
    if custom_terms_json:
        terms_list = []
        for term in custom_terms_json["terms"]:
            terms_list.append(f"- {term['src']}: {term['tgt']} ({term['note']})")
        terms_note = "\n### 已有术语\n请在提取时排除以下术语：\n" + "\n".join(
            terms_list
        )

    summary_prompt = f"""
## 角色
你是一名视频翻译专家和术语顾问，专长于 {src_lang} 理解和 {tgt_lang} 表达优化。

## 任务
针对提供的 {src_lang} 视频文本：
1. 用两句话总结主题
2. 提取专业术语/名称并附上 {tgt_lang} 翻译（排除已有术语）
3. 为每个术语提供简要说明

{terms_note}

步骤：
1. 主题总结：
   - 快速浏览获取整体理解
   - 写两句话：第一句描述主题，第二句描述要点
2. 术语提取：
   - 标记专业术语和名称（排除"已有术语"中列出的）
   - 提供 {tgt_lang} 翻译或保留原文
   - 添加简要说明
   - 提取不超过15个术语

## 输入
<text>
{source_content}
</text>

## 仅以 JSON 格式输出，不要添加其他文本
{{
  "theme": "两句话的视频总结",
  "terms": [
    {{
      "src": "{src_lang} 术语",
      "tgt": "{tgt_lang} 翻译或原文", 
      "note": "简要说明"
    }},
    ...
  ]
}}  

## 示例
{{
  "theme": "本视频介绍人工智能在医疗领域的应用现状。重点展示了AI在医学影像诊断和药物研发中的突破性进展。",
  "terms": [
    {{
      "src": "Machine Learning",
      "tgt": "机器学习",
      "note": "AI的核心技术，通过数据训练实现智能决策"
    }},
    {{
      "src": "CNN",
      "tgt": "CNN",
      "note": "卷积神经网络，用于医学图像识别的深度学习模型"
    }}
  ]
}}

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
""".strip()
    return summary_prompt


## ================================================================
# @ step5_translate.py & translate_lines.py
def generate_shared_prompt(
    previous_content_prompt, after_content_prompt, summary_prompt, things_to_note_prompt
):
    return f"""### 上下文信息
<previous_content>
{previous_content_prompt}
</previous_content>

<subsequent_content>
{after_content_prompt}
</subsequent_content>

### 内容摘要
{summary_prompt}

### 注意事项
{things_to_note_prompt}"""


def get_prompt_faithfulness(lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    # 按换行符分割
    line_splits = lines.split("\n")

    json_dict = {}
    for i, line in enumerate(line_splits, 1):
        json_dict[f"{i}"] = {
            "origin": line,
            "direct": f"直译 {TARGET_LANGUAGE} 翻译 {i}.",
        }
    json_format = json.dumps(json_dict, indent=2, ensure_ascii=False)

    # 如果用户指定了语言则使用，否则使用检测到的语言
    user_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language")
    src_language = (
        user_language
        if user_language and user_language != "auto"
        else detected_language
    )
    src_language = get_language_name(src_language)  # 将语言代码转换为完整名称供LLM使用
    prompt_faithfulness = f"""
## 角色
你是一名专业的 Netflix 字幕翻译专家，精通 {src_language} 和 {TARGET_LANGUAGE}，以及两种语言的文化背景。
你的专长在于准确理解原始 {src_language} 文本的语义和结构，并在保持原意的同时忠实地翻译成 {TARGET_LANGUAGE}。

## 任务
我们有一段原始 {src_language} 字幕需要直译成 {TARGET_LANGUAGE}。这些字幕来自特定的上下文，可能包含特定的主题和术语。

1. 将原始 {src_language} 字幕逐行翻译成 {TARGET_LANGUAGE}
2. 确保翻译忠实于原文，准确传达原意
3. 考虑上下文和专业术语

{shared_prompt}

<翻译原则>
1. 忠实于原文：准确传达原文的内容和含义，不随意更改、添加或删减内容。
2. 术语准确：正确使用专业术语，保持术语一致性。
3. 理解上下文：充分理解并反映文本的背景和上下文关系。
</翻译原则>

## 输入
<subtitles>
{lines}
</subtitles>

## 仅以 JSON 格式输出，不要添加其他文本
```json
{json_format}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
"""
    return prompt_faithfulness.strip()


def get_prompt_expressiveness(faithfulness_result, lines, shared_prompt):
    TARGET_LANGUAGE = load_key("target_language")
    json_format = {
        key: {
            "origin": value["origin"],
            "direct": value["direct"],
            "reflect": "你对直译的反思",
            "free": "你的意译",
        }
        for key, value in faithfulness_result.items()
    }
    json_format = json.dumps(json_format, indent=2, ensure_ascii=False)

    # 如果用户指定了语言则使用，否则使用检测到的语言
    user_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language")
    src_language = (
        user_language
        if user_language and user_language != "auto"
        else detected_language
    )
    src_language = get_language_name(src_language)  # 将语言代码转换为完整名称供LLM使用
    prompt_expressiveness = f"""
## 角色
你是一名专业的 Netflix 字幕翻译专家和语言顾问。
你的专长不仅在于准确理解原始 {src_language}，还在于优化 {TARGET_LANGUAGE} 翻译，使其更符合目标语言的表达习惯和文化背景。

## 任务
我们已经有了原始 {src_language} 字幕的直译版本。
你的任务是反思和改进这些直译，创作出更自然流畅的 {TARGET_LANGUAGE} 字幕。

1. 逐行分析直译结果，指出存在的问题
2. 提供详细的修改建议
3. 根据你的分析进行意译
4. 翻译中不要添加注释或解释，因为字幕是给观众看的
5. 意译中不要留空行，因为字幕是给观众看的

{shared_prompt}

<翻译分析步骤>
请使用两步思考过程逐行处理文本：

1. 直译反思：
   - 评估语言流畅性
   - 检查语言风格是否与原文一致
   - 检查字幕的简洁性，指出翻译过于冗长的地方

2. {TARGET_LANGUAGE} 意译：
   - 追求上下文的流畅自然，符合 {TARGET_LANGUAGE} 表达习惯
   - 确保 {TARGET_LANGUAGE} 观众容易理解和接受
   - 根据主题调整语言风格（例如：教程使用口语化表达，技术内容使用专业术语，纪录片使用正式语言）
</翻译分析步骤>
   
## 输入
<subtitles>
{lines}
</subtitles>

## 仅以 JSON 格式输出，不要添加其他文本
```json
{json_format}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
"""
    return prompt_expressiveness.strip()


## ================================================================
# @ step6_splitforsub.py
def get_align_prompt(src_sub, tr_sub, src_part):
    targ_lang = load_key("target_language")
    # 如果用户指定了语言则使用，否则使用检测到的语言
    user_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language")
    src_lang = (
        user_language
        if user_language and user_language != "auto"
        else detected_language
    )
    src_splits = src_part.split("\n")
    num_parts = len(src_splits)
    src_part = src_part.replace("\n", " [br] ")
    align_parts_json = ",".join(
        f'''
        {{
            "src_part_{i + 1}": "{src_splits[i]}",
            "target_part_{i + 1}": "对应对齐的 {targ_lang} 字幕部分"
        }}'''
        for i in range(num_parts)
    )

    align_prompt = f'''
## 角色
你是一名 Netflix 字幕对齐专家，精通 {src_lang} 和 {targ_lang}。

## 任务
我们有一个 Netflix 节目的 {src_lang} 和 {targ_lang} 原始字幕，以及预处理过的 {src_lang} 字幕分割版本。
你的任务是根据这些信息为 {targ_lang} 字幕创建最佳分割方案。

1. 分析 {src_lang} 和 {targ_lang} 字幕之间的词序和结构对应关系
2. 根据预处理的 {src_lang} 分割版本分割 {targ_lang} 字幕
3. 不要留空行。如果难以按语义分割，可以适当改写需要对齐的句子
4. 翻译中不要添加注释或解释，因为字幕是给观众看的

## 输入
<subtitles>
{src_lang} 原文: "{src_sub}"
{targ_lang} 原文: "{tr_sub}"
预处理 {src_lang} 字幕（[br] 表示分割点）: {src_part}
</subtitles>

## 仅以 JSON 格式输出，不要添加其他文本
```json
{{
    "analysis": "简要分析两种字幕之间的词序、结构和语义对应关系",
    "align": [
        {align_parts_json}
    ]
}}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
'''.strip()
    return align_prompt


## ================================================================
# @ step8_gen_audio_task.py @ step10_gen_audio.py
def get_subtitle_trim_prompt(text, duration):
    rule = """考虑以下几点：a. 减少填充词而不修改有意义的内容。b. 省略不必要的修饰语或代词，例如：
    - "请解释一下你的思考过程" 可以缩短为 "请解释思考过程"
    - "我们需要仔细分析这个复杂的问题" 可以缩短为 "我们需要分析这个问题"
    - "让我们讨论一下关于这个话题的各种不同观点" 可以缩短为 "让我们讨论这个话题的不同观点"
    - "你能详细描述一下你昨天的经历吗" 可以缩短为 "你能描述昨天的经历吗" """

    trim_prompt = f'''
## 角色
你是一名专业的字幕编辑，负责在将超时字幕交给配音演员之前进行编辑和优化。
你的专长在于巧妙地略微缩短字幕，同时确保原意和结构保持不变。

## 输入
<subtitles>
字幕: "{text}"
时长: {duration} 秒
</subtitles>

## 处理规则
{rule}

## 处理步骤
请按照以下步骤操作，并在 JSON 输出中提供结果：
1. 分析：简要分析字幕的结构、关键信息以及可以省略的填充词。
2. 精简：根据规则和分析，按照处理规则优化字幕使其更简洁。

## 仅以 JSON 格式输出，不要添加其他文本
```json
{{
    "analysis": "简要分析字幕，包括结构、关键信息和可能的处理位置",
    "result": "优化精简后的字幕，使用原字幕语言"
}}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
'''.strip()
    return trim_prompt


## ================================================================
# @ tts_main
def get_correct_text_prompt(text):
    return f"""
## 角色
你是一名 TTS（文本转语音）系统的文本清理专家。

## 任务
清理给定文本：
1. 只保留基本标点符号（.,?!）
2. 保持原意不变

## 输入
{text}

## 仅以 JSON 格式输出，不要添加其他文本
```json
{{
    "text": "清理后的文本"
}}
```

注意：你的回答必须以 ```json 开头，以 ``` 结尾，不要添加任何其他文本。
""".strip()
