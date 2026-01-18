import spacy

nlp = spacy.load('ja_core_news_md')

# 测试文本 - 没有标点的日语（ASR 输出的典型情况）
texts = [
    '少しお話ししたいことがございますので我輩の屋敷にお越しいただけますかね何のつもりですかな',
    '高レベルの警戒隠蔽を使うことはヨガラスのカメラを通して見ていたのでなお前が王女につきまとっていると知りサラムの魔眼に似せた仕組みを作らせたのだ',
    # 带标点的对比
    '少しお話ししたいことがございます。我輩の屋敷にお越しいただけますかね。何のつもりですかな。',
]

for text in texts:
    print('='*60)
    print(f'文本: {text[:50]}...' if len(text) > 50 else f'文本: {text}')
    print(f'长度: {len(text)} 字符')
    
    doc = nlp(text)
    print(f'has_annotation SENT_START: {doc.has_annotation("SENT_START")}')
    
    sents = list(doc.sents)
    print(f'spaCy 检测到 {len(sents)} 个句子:')
    for i, sent in enumerate(sents):
        print(f'  {i+1}: [{len(sent.text)}字] {sent.text}')
    print()
