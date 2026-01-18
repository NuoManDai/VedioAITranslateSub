from difflib import SequenceMatcher

original = 'りサラムの魔眼に似せた仕組みを作らせ'
modified = 'りサラムの魔眼に[br]似せた仕組みを作らせ'
parts = modified.split('[br]')
print('Parts:', parts)
print('Original length:', len(original))

best_j = None
max_sim = 0
for j in range(len(original)):
    original_left = original[0:j]
    modified_left = ''.join(parts[0].split())
    sim = SequenceMatcher(None, original_left, modified_left).ratio()
    if sim > max_sim:
        max_sim = sim
        best_j = j
    if sim > 0.8:
        print(f'j={j}, sim={sim:.3f}, original_left="{original_left}"')

print(f'\nBest: j={best_j}, sim={max_sim:.3f}')
print(f'Split result: "{original[:best_j]}" | "{original[best_j:]}"')
