import pandas as pd

df = pd.read_excel('output/log/cleaned_chunks.xlsx')
df['text'] = df['text'].apply(lambda x: str(x).strip('"').strip())
df['gap'] = df['start'].shift(-1) - df['end']

# 找出有明显 gap 的位置
gaps = df[df['gap'] > 0.1]
print(f'Gaps > 0.1s: {len(gaps)}')
print(gaps[['text', 'gap']].to_string())
