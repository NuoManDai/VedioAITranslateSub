import pandas as pd

df = pd.read_excel('d:/1-work_data/videoLongo/output/log/cleaned_chunks.xlsx')
df['text'] = df['text'].apply(lambda x: str(x).strip('"').strip())

# 合并所有文本
text_all = ''.join(df['text'].tolist())
print(f"总文本长度: {len(text_all)}")
print(f"文本内容: {text_all[:200]}...")

# 句尾模式
enders = ['ます', 'です', 'ました', 'でした', 'ません', 'ください', 'ましょう']

for ender in enders:
    count = text_all.count(ender)
    if count > 0:
        print(f'{ender}: {count} occurrences')
