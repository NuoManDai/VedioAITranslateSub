import os
import re
import pandas as pd
import warnings
from core.spacy_utils.load_nlp_model import init_nlp, SPLIT_BY_MARK_FILE
from core.utils.config_utils import load_key, get_joiner
from rich import print as rprint

warnings.filterwarnings("ignore", category=FutureWarning)

def split_sentence_by_time_gap(sentence: str, chunks: pd.DataFrame, joiner: str, threshold: float) -> list[str]:
    """
    对单个句子，检查其内部是否有超过阈值的时间间隔，如果有则切分。
    通过逐字符匹配把句子映射回 chunks，然后检查时间信息。
    """
    if not sentence.strip():
        return [sentence]
    
    # 找到这个句子对应的 chunks 范围
    # 策略：按顺序匹配 chunks 的 text
    result_segments = []
    current_segment = []
    
    # 计算时间信息
    chunks_copy = chunks.copy()
    chunks_copy['duration'] = chunks_copy['end'] - chunks_copy['start']
    chunks_copy['gap_to_next'] = chunks_copy['start'].shift(-1) - chunks_copy['end']
    
    # 把句子拆成字符，逐个匹配 chunks
    remaining_sentence = sentence
    
    for idx, row in chunks_copy.iterrows():
        chunk_text = str(row['text']).strip('"').strip('"').replace('"', '').strip()
        duration = row.get('duration', 0)
        gap_to_next = row.get('gap_to_next', 0)
        
        # 检查这个 chunk 是否在当前句子中
        if joiner:
            # 有连接符的语言（如英语），chunk 可能带空格
            if remaining_sentence.startswith(chunk_text):
                remaining_sentence = remaining_sentence[len(chunk_text):].lstrip()
                current_segment.append(chunk_text)
            elif remaining_sentence.startswith(chunk_text + joiner):
                remaining_sentence = remaining_sentence[len(chunk_text + joiner):]
                current_segment.append(chunk_text)
            else:
                continue  # 这个 chunk 不在当前句子中
        else:
            # 无连接符的语言（如日语、中文）
            if chunk_text in remaining_sentence:
                pos = remaining_sentence.find(chunk_text)
                if pos == 0:
                    remaining_sentence = remaining_sentence[len(chunk_text):]
                    current_segment.append(chunk_text)
                else:
                    continue
            else:
                continue
        
        # 检查是否需要在此处切分
        should_split = False
        if duration > threshold:
            should_split = True
        elif pd.notna(gap_to_next) and gap_to_next > threshold:
            should_split = True
        
        if should_split and remaining_sentence:  # 还有剩余内容才切分
            result_segments.append(joiner.join(current_segment))
            current_segment = []
    
    # 添加最后一段
    if current_segment:
        result_segments.append(joiner.join(current_segment))
    
    # 如果没有匹配成功，返回原句子
    if not result_segments:
        return [sentence]
    
    return result_segments


def split_by_mark(nlp):
    whisper_language = load_key("whisper.language")
    language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language
    joiner = get_joiner(language)
    rprint(f"[blue]🔍 Using {language} language joiner: '{joiner}'[/blue]")
    segments_path = "output/log/segments.xlsx"
    chunks_path = "output/log/cleaned_chunks.xlsx"

    def has_punctuation(text_list: list) -> bool:
        punctuation_marks = {"。", "、", "！", "？", ".", ",", "!", "?", "；", "：", ";", ":"}
        if not text_list:
            return False
        lines_with_punc = 0
        for item in text_list:
            if any(mark in item for mark in punctuation_marks):
                lines_with_punc += 1
        ratio = lines_with_punc / max(len(text_list), 1)
        return ratio >= 0.2

    if os.path.exists(segments_path):
        segments_df = pd.read_excel(segments_path)
        if "text" not in segments_df.columns:
            raise ValueError("segments.xlsx missing required column: text")
        base_sentences = segments_df["text"].astype(str).tolist()
        use_segments_base = not has_punctuation(base_sentences)
        if use_segments_base:
            rprint("[blue]🧩 Using segments.xlsx as sentence base (no punctuation detected)[/blue]")
        else:
            rprint("[blue]🧩 segments.xlsx has punctuation, using spaCy split[/blue]")
    else:
        chunks = pd.read_excel(chunks_path)
        base_sentences = chunks["text"].astype(str).tolist()
        rprint("[yellow]⚠️ segments.xlsx not found, fallback to cleaned_chunks.xlsx[/yellow]")
        use_segments_base = False
    
    # 从配置读取时间间隔阈值
    try:
        time_gap_threshold = load_key("time_gap_threshold")
    except KeyError:
        time_gap_threshold = None
    
    if time_gap_threshold and time_gap_threshold > 0:
        rprint(f"[blue]⏱️ Time gap threshold enabled: {time_gap_threshold}s[/blue]")
    
    base_sentences = [
        str(text).strip('"').strip('"').replace('"', '').strip() for text in base_sentences
    ]

    if use_segments_base:
        sentences_by_mark = [sentence for sentence in base_sentences if sentence.strip()]
        rprint(f"[blue]📊 Using {len(sentences_by_mark)} segment sentences directly[/blue]")
    else:
        # Step 1: 先用 spaCy 根据标点切分
        full_text = joiner.join(base_sentences)
        doc = nlp(full_text)
        assert doc.has_annotation("SENT_START")

        # 处理 - 和 ... 的情况
        spacy_sentences = []
        current_sentence = []
        
        for sent in doc.sents:
            text = sent.text.strip()
            
            if current_sentence and (
                text.startswith('-') or 
                text.startswith('...') or
                current_sentence[-1].endswith('-') or
                current_sentence[-1].endswith('...')
            ):
                current_sentence.append(text)
            else:
                if current_sentence:
                    spacy_sentences.append(joiner.join(current_sentence))
                    current_sentence = []
                current_sentence.append(text)
        
        if current_sentence:
            spacy_sentences.append(joiner.join(current_sentence))
        
        rprint(f"[blue]📊 spaCy split into {len(spacy_sentences)} sentences[/blue]")
        
        # Step 2: 如果启用了时间切分，对每个 spaCy 句子再检查时间间隔
        sentences_by_mark = []
        
        if time_gap_threshold and time_gap_threshold > 0:
            # 需要重新加载原始 chunks（带时间信息）
            chunks_with_time = pd.read_excel(chunks_path)
            chunks_with_time['duration'] = chunks_with_time['end'] - chunks_with_time['start']
            chunks_with_time['gap_to_next'] = chunks_with_time['start'].shift(-1) - chunks_with_time['end']
            
            # 用一个全局指针追踪当前处理到哪个 chunk
            chunk_idx = 0
            total_chunks = len(chunks_with_time)
            time_split_count = 0
            
            for sentence in spacy_sentences:
                if not sentence.strip():
                    continue
                
                # 收集当前句子对应的 chunks 及其时间信息
                current_segment = []
                sentence_remaining = sentence
                
                while chunk_idx < total_chunks and sentence_remaining:
                    row = chunks_with_time.iloc[chunk_idx]
                    chunk_text = str(row['text']).strip('"').strip('"').replace('"', '').strip()
                    duration = row['duration']
                    gap_to_next = row['gap_to_next'] if pd.notna(row['gap_to_next']) else 0
                    
                    # 检查这个 chunk 是否在剩余句子中
                    if joiner:
                        check_text = chunk_text
                        if sentence_remaining.startswith(check_text):
                            sentence_remaining = sentence_remaining[len(check_text):].lstrip()
                            current_segment.append(chunk_text)
                            chunk_idx += 1
                        else:
                            break  # 当前 chunk 不匹配，说明句子处理完了
                    else:
                        # 日语/中文等无空格语言
                        if sentence_remaining.startswith(chunk_text):
                            sentence_remaining = sentence_remaining[len(chunk_text):]
                            current_segment.append(chunk_text)
                            chunk_idx += 1
                        else:
                            break
                    
                    # 检查是否需要在此处切分（还有剩余内容才切）
                    should_split = (duration > time_gap_threshold or gap_to_next > time_gap_threshold)
                    
                    if should_split and sentence_remaining:
                        sentences_by_mark.append(joiner.join(current_segment))
                        current_segment = []
                        time_split_count += 1
                
                # 添加当前句子的最后一段
                if current_segment:
                    sentences_by_mark.append(joiner.join(current_segment))
            
            if time_split_count > 0:
                rprint(f"[blue]⏱️ Time gap made {time_split_count} additional cuts[/blue]")
        else:
            sentences_by_mark = spacy_sentences

    rprint(f"[blue]📊 Final: {len(sentences_by_mark)} sentences[/blue]")
    
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
