'''
 使用LangGraph复现吴恩达博士的翻译Workflow项目
'''

import openai #采用OpenAI的Py封装调用模型
import pygraphviz as pygv #系统绘制工具
from langgraph.graph import StateGraph,START,END
from typing import TypedDict,Optional

# 配置国产模型 DeepSeek
deep_seek_url = "https://api.siliconflow.cn/v1"
deep_seek_api_key = "your_api_key"
deep_seek_default_model = "deepseek-ai/DeepSeek-V2.5"

# 模型请求准备
client = openai.OpenAI(
    api_key = deep_seek_api_key,
    base_url = deep_seek_url
)

# 一次大模型对话
def get_completion(
        prompt:str,
        system_message:str = "你是一个智能助手",
        model:str = deep_seek_default_model,
        temperature:float = 0.3,
)->str:
    response = client.chat.completions.create(
        model = model,  #指定使用的模型
        temperature=temperature,  #控制输出的随机性/创造性 (0-1) - 0: 更确定性的输出 - 1: 更随机/创造性的输出
        top_p=1, # 核采样阈值 (0-1)，控制模型在生成文本时考虑的词汇范围，1 表示考虑所有可能性
        messages=[  #对话历史
            {"role":"system","content":system_message}, #设置AI助手的角色/行为
            {"role": "user", "content":prompt} #用户的实际提问/输入
        ]
    )
    return response.choices[0].message.content

# 定义传递的信息结构
class State(TypedDict):
    source_lang: str                # 源语言
    target_lang: str                # 目标语言
    source_text: str                # 源文本
    country: str                    # 国家
    translation_1: Optional[str]    # 翻译1
    reflection: Optional[str]       # 反思
    translation_2: Optional[str]    # 翻译2

workflow = StateGraph(State) # 创建一个工作流对象

# 初次翻译的工作块
def initial_translation(state:State)->State:
    source_lang = state.get("source_lang")  #翻译的源语言
    target_lang = state.get("target_lang")  #翻译的目标语言
    source_text = state.get("source_text")  #翻译的源文本

    system_message = f"你是一名翻译专家，你擅长{source_lang}到{target_lang}的翻译工作。" #系统消息

    # 构建一个提示词
    prompt = f"""这是一个从{source_lang}到{target_lang}的翻译任务，请你完成将目标语言为{target_lang}的翻译，最终输出翻译后的文本。
    除了翻译之外，不要再提供任何其他解释或其他文字。
    {source_lang}: {source_text}


    {target_lang}:
    """

    translation = get_completion(prompt,system_message) #调用模型进行翻译

    print("[初次翻译的结果]：\n",translation)

    return {"translation_1":translation}

# 进行反思翻译的工作块
def reflect_on_translation(state:State)->State:
    source_lang = state.get("source_lang")
    target_lang = state.get("target_lang")
    source_text = state.get("source_text")
    country = state.get("country")
    translation_1 = state.get("translation_1")

    system_message = f"""你是一名专业的语言专家，你擅长{target_lang}到{source_lang}的翻译工作。
    你将获得源文本及其翻译的译文，而你现在的目标是改进这个翻译。"""
    
    # 定义一个附加规则
    addittional_rule = (
        f"""翻译的最终风格和语气应该与{country}的文化和语言习惯相匹配。""" if country != "" else ""
    )

    prompt = f"""你的任务是仔细阅读源文本和从{source_lang}到{target_lang}的译文,然后给出建设性的批评和有益的建议以改进翻译。
    {addittional_rule}
    源文本和初始译文以 XML 标签：<SOURCE_TEXT></SOURCE_TEXT> 和 <TRANSLATION></TRANSLATION>分割。如下所示：

    <SOURCE_TEXT>
    {source_text}
    </SOURCE_TEXT>

    <TRANSLATION>
    {translation_1}
    </TRANSLATION>
    
    在撰写翻译时，请注意额是否有有方法可以改进翻译的：
    1.准确性：通过纠正添加、误译、遗漏或未翻译文本的错误；
    2.流畅性：通过应用{target_lang}语法、拼写和标点规则，并确保没有不必要的重复；
    3.风格：通过确保翻译反映源文本的风格和语气与文化背景相匹配；
    4.术语：通过确保术语使用一致并反映源文本领域，并且确保使用等效习语{target_lang}；

    要列出具体的、有用的且有建设性的反馈，以帮助改进翻译。
    每个建议应针对翻译的一个特定部分。

    仅输出建议，不要输出其他内容。
    """
    reflection = get_completion(prompt,system_message) #调用模型进行反思建议

    print("[反思后的建议结果]：\n",reflection)

    return{"reflection":reflection}

def improve_translation(state:State)->State:
    source_lang = state.get("source_lang")
    target_lang = state.get("target_lang")
    source_text = state.get("source_text")
    translation_1 = state.get("translation_1")
    reflection = state.get("reflection")

    system_message = f"""你是一名专业的语言专家，你擅长{target_lang}到{source_lang}的翻译工作。"""

    prompt = f"""
    你的任务是仔细阅读文本，然后编辑从{source_lang}到{target_lang}的翻译,同时你需要考虑专家给到的有益性建议和建设性批评。
    源文本、初始化翻译和专家语言学家的建议由 XML 标签<SOURCE_TEXT></SOURCE_TEXT>、<TRANSLATION></TRANSLATION>和<EXPERT_SUGGESTIONS></EXPERT_SUGGESTIONS>分割。如下所示：

    <SOURCE_TEXT>
    {source_text}
    </SOURCE_TEXT>

    <TRANSLATION>
    {translation_1}
    </TRANSLATION>

    <EXPERT_SUGGESTIONS>
    {reflection}
    </EXPERT_SUGGESTIONS>

    在撰写翻译时，请考虑专家的建议，并确保：
    1.准确性：通过纠正添加、误译、遗漏或未翻译文本的错误；
    2.流畅性：通过应用{target_lang}语法、拼写和标点规则，并确保没有不必要的重复；
    3.风格：通过确保翻译反映源文本的风格和语气与文化背景相匹配；
    4.术语：通过确保术语使用一致并反映源文本领域，并且确保使用等效习语{target_lang}；
    5.是否有其他错误；

    仅输出新的译文，不要输出其他内容。
    """

    translation_2 = get_completion(prompt,system_message) #调用模型进行翻译

    print("[改进后的翻译结果]：\n",translation_2)

    return{"translation_2":translation_2}

# 规划执行任务
# 工作流的节点注册
workflow.add_node("initial_translation",initial_translation)
workflow.add_node("reflect_on_translation",reflect_on_translation)
workflow.add_node("improve_translation",improve_translation)
# 工作流的边注册
workflow.add_edge(START,"initial_translation")
workflow.add_edge("initial_translation","reflect_on_translation")
workflow.add_edge("reflect_on_translation","improve_translation")
workflow.add_edge("improve_translation",END)

# 编译工作流
graph = workflow.compile()

# 绘制工作流图
graph.get_graph().draw_png("translate_workflow.png")

# 数据准备
data = {
    'source_lang':'English',
    'target_lang':'Chinese',
    'country':'中国',
    'source_text':"""
    In this report, we introduce the ChatGLM family of large language models from GLM-130B to
GLM-4 (All Tools). Over the past one and half years, we have made great progress in understanding
various perspectives of large language models from our first-hand experiences. With the development
of each model generation, the team has learned and applied more effective and efficient strategies
for both model pre-training and alignment. The recent ChatGLM models—GLM-4 (0116, 0520),
GLM-4-Air (0605), and GLM-4 All Tools—demonstrate significant advancements in understanding
and executing complex tasks by autonomously employing external tools and functions. These GLM-4
models have achieved performance on par with, and in some cases surpassing, state-of-the-art models
such as GPT-4 Turbo, Claude 3 Opus, and Gemini 1.5 Pro, particularly in handling tasks relevant to
the Chinese language. In addition, we are committed to promoting accessibility and safety of LLMs
through open releasing of our model weights and techniques developed throughout this journey. Our
open models, including language, code, and vision models, have attracted over 10 million downloads
on Hugging Face in the year 2023 alone. Currently, we are working on more capable models with
everything we have learned to date. In the future, we will continue democratizing cutting-edge LLM
technologies through open sourcing, and push the boundary of model capabilities towards the mission
of teaching machines to think like humans.
Acknowledgement. We would like to thank all the data annotators, infra operating staffs, collaborators, and partners as well as everyone at Zhipu AI and Tsinghua University not explicitly mentioned in
the report who have provided support, feedback, and contributed to ChatGLM. We would also like to
thank Yuxuan Zhang and Wei Jia from Zhipu AI as well as the teams at Hugging Face, ModelScope,
WiseModel, and others for their help on the open-sourcing efforts of the GLM family of models.
    """
}

# 执行工作流
result = graph.invoke(data)