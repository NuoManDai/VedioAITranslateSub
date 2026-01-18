import os
import re
import pandas as pd
import warnings
from core.spacy_utils.load_nlp_model import init_nlp, SPLIT_BY_MARK_FILE
from core.utils.config_utils import load_key, get_joiner
from rich import print as rprint

warnings.filterwarnings("ignore", category=FutureWarning)

def split_by_time_gap(chunks: pd.DataFrame, joiner: str, threshold: float) -> list[str]:
    """
    根据单词持续时间进行预切分
    如果某个单词的 (end - start) > threshold 秒，说明是自然停顿点，在此处切分
    """
    segments = []
    current_segment = []
    split_count = 0
    
    for idx, row in chunks.iterrows():
        text = str(row['text']).strip('"').strip('"').replace('"', '').strip()
        start = row.get('start', 0)
        end = row.get('end', 0)
        duration = end - start
        
        current_segment.append(text)
        
        # 如果当前单词持续时间超过阈值，在此处切分
        if duration > threshold:
            segments.append(joiner.join(current_segment))
            current_segment = []
            split_count += 1
    
    # 添加最后一个片段
    if current_segment:
        segments.append(joiner.join(current_segment))
    
    if split_count > 0:
        rprint(f"[blue]⏱️ Split by time gap (>{threshold}s): {split_count} cuts[/blue]")
    
    return segments

def split_by_mark(nlp):
    whisper_language = load_key("whisper.language")
    language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language
    joiner = get_joiner(language)
    rprint(f"[blue]🔍 Using {language} language joiner: '{joiner}'[/blue]")
    chunks = pd.read_excel("output/log/cleaned_chunks.xlsx")
    
    # 从配置读取时间间隔阈值，如果为空或0则不启用
    time_gap_threshold = load_key("time_gap_threshold")
    
    if time_gap_threshold and time_gap_threshold > 0:
        # Step 1: 先根据时间间隔预切分
        rprint(f"[blue]⏱️ Time gap threshold enabled: {time_gap_threshold}s[/blue]")
        time_segments = split_by_time_gap(chunks, joiner, time_gap_threshold)
    else:
        # 不启用时间切分，直接拼接全部文本
        chunks.text = chunks.text.apply(lambda x: str(x).strip('"').strip('"').replace('"', '').strip())
        time_segments = [joiner.join(chunks.text.to_list())]
    
    # Step 2: 对每个时间片段再用 spaCy 进行标点切分
    sentences_by_mark = []
    
    for segment in time_segments:
        if not segment.strip():
            continue
            
        doc = nlp(segment)
        assert doc.has_annotation("SENT_START")

        # skip - and ...
        current_sentence = []
        
        # iterate all sentences in this segment
        for sent in doc.sents:
            text = sent.text.strip()
            
            # check if the current sentence ends with - or ...
            if current_sentence and (
                text.startswith('-') or 
                text.startswith('...') or
                current_sentence[-1].endswith('-') or
                current_sentence[-1].endswith('...')
            ):
                current_sentence.append(text)
            else:
                if current_sentence:
                    sentences_by_mark.append(joiner.join(current_sentence))
                    current_sentence = []
                current_sentence.append(text)
        
        # add the last sentence of this segment
        if current_sentence:
            sentences_by_mark.append(joiner.join(current_sentence))

    rprint(f"[blue]📊 Split into {len(sentences_by_mark)} sentences[/blue]")
    
    with open(SPLIT_BY_MARK_FILE, "w", encoding="utf-8") as output_file:
        for i, sentence in enumerate(sentences_by_mark):
            if i > 0 and sentence.strip() in [',', '.', '，', '。', '？', '！']:
                # ! If the current line contains only punctuation, merge it with the previous line, this happens in Chinese, Japanese, etc.
                output_file.seek(output_file.tell() - 1, os.SEEK_SET)  # Move to the end of the previous line
                output_file.write(sentence)  # Add the punctuation
            else:
                output_file.write(sentence + "\n")
    
    rprint(f"[green]💾 Sentences split by punctuation marks saved to →  `{SPLIT_BY_MARK_FILE}`[/green]")

if __name__ == "__main__":
    nlp = init_nlp()
    split_by_mark(nlp)
