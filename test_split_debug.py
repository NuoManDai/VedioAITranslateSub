import sys
sys.path.insert(0, 'd:/1-work_data/videoLongo')

from core.spacy_utils.load_nlp_model import init_nlp
from core._3_2_split_meaning import tokenize_sentence, find_split_positions
from core.utils import load_key
from difflib import SequenceMatcher

# 测试第17行的长句子
sentence = "高レベルの警戒隠蔽を使うことはヨガラスのカメラを通して見ていたのでなお前が王女につきまとっていると知りサラムの魔眼に似せた仕組みを作らせたのだ"

print(f"原句长度: {len(sentence)} 字符")
print(f"原句: {sentence}\n")

# 初始化 NLP
nlp = init_nlp()

# 分词
tokens = tokenize_sentence(sentence, nlp)
print(f"Token 数量: {len(tokens)}")
print(f"Tokens: {tokens[:20]}... (前20个)")

# 模拟 GPT 返回（假设在 "知り" 后面分割）
gpt_response = "高レベルの警戒隠蔽を使うことはヨガラスのカメラを通して見ていたのでなお前が王女につきまとっていると知り[br]サラムの魔眼に似せた仕組みを作らせたのだ"

# 测试 find_split_positions
split_positions = find_split_positions(sentence, gpt_response)
print(f"\n分割点位置: {split_positions}")

if split_positions:
    for pos in split_positions:
        print(f"分割点 {pos}: '{sentence[:pos]}' | '{sentence[pos:]}'")
else:
    print("没有找到分割点！")

# 检查 joiner 设置
from core.utils import get_joiner
whisper_language = load_key("whisper.language")
language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language
joiner = get_joiner(language)
print(f"\n语言: {language}, Joiner: '{joiner}'")

# 手动测试相似度计算
parts = gpt_response.split('[br]')
print(f"\nGPT 分割的 parts: {parts}")

modified_left = joiner.join(parts[0].split())
print(f"modified_left: '{modified_left}'")

# 找最佳分割点
best_j = 0
max_sim = 0
for j in range(len(sentence)):
    original_left = sentence[0:j]
    sim = SequenceMatcher(None, original_left, modified_left).ratio()
    if sim > max_sim:
        max_sim = sim
        best_j = j

print(f"\n最佳分割点: j={best_j}, 相似度={max_sim:.3f}")
print(f"original_left: '{sentence[:best_j]}'")
