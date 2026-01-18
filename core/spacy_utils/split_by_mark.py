import os
import re
import pandas as pd
import warnings
from core.spacy_utils.load_nlp_model import init_nlp, SPLIT_BY_MARK_FILE
from core.utils.config_utils import load_key, get_joiner
from rich import print as rprint

warnings.filterwarnings("ignore", category=FutureWarning)

# Japanese sentence-ending particles and expressions
JA_SENTENCE_ENDERS = [
    # Polite endings (most reliable)
    'ます', 'です', 'ました', 'でした', 'ません', 'ください', 'ましょう',
    # Plain verb endings
    'だ', 'た', 'る',
    # Sentence-final particles
    'ね', 'よ', 'わ', 'ぞ', 'な', 'さ', 'の', 'か',
    # Combined particles
    'かな', 'かね', 'かしら', 'よね', 'のよ', 'わよ',
    # Explanatory forms
    'んだ', 'のだ', 'んです', 'のです',
    # Quotative
    'と',
]

def split_japanese_by_time_and_grammar(chunks_df, nlp, gap_threshold=0.3):
    """
    Split Japanese text by combining time gaps and grammatical patterns.
    Since Japanese ASR often lacks punctuation, we use:
    1. Time gaps between chunks (indicating pauses)
    2. Sentence-ending particles and verb forms
    3. Punctuation marks (! ? etc.)
    """
    chunks = chunks_df.copy()
    chunks['text'] = chunks['text'].apply(lambda x: str(x).strip('"').strip('"').replace('"', '').strip())
    
    # Calculate time gaps
    chunks['gap'] = chunks['start'].shift(-1) - chunks['end']
    
    sentences = []
    current_sentence = []
    current_start = None
    
    for i, row in chunks.iterrows():
        if current_start is None:
            current_start = row['start']
        
        current_sentence.append(row['text'])
        current_text = ''.join(current_sentence)
        
        should_split = False
        
        # Check for punctuation marks (highest priority)
        if row['text'] in ['!', '?', '？', '！', '。', '．']:
            should_split = True
        # Check for significant time gap (strong indicator of sentence boundary)
        elif pd.notna(row['gap']) and row['gap'] > gap_threshold:
            should_split = True
        # Check for sentence-ending patterns with small gap
        elif len(current_text) >= 3 and pd.notna(row['gap']) and row['gap'] > 0.08:
            # Check polite endings (very reliable)
            for ender in ['ます', 'です', 'ました', 'でした', 'ません', 'ください', 'ましょう']:
                if current_text.endswith(ender):
                    should_split = True
                    break
            # Check sentence-final particles (reliable with gap)
            if not should_split and row['gap'] > 0.15:
                for ender in ['ね', 'よ', 'わ', 'ぞ', 'な', 'さ', 'の', 'か', 'よね', 'かな', 'かね']:
                    if current_text.endswith(ender):
                        should_split = True
                        break
        
        if should_split and current_sentence:
            sentences.append(''.join(current_sentence))
            current_sentence = []
            current_start = None
    
    # Add remaining text
    if current_sentence:
        sentences.append(''.join(current_sentence))
    
    # Post-process: merge very short sentences (< 2 chars) with next
    merged_sentences = []
    i = 0
    while i < len(sentences):
        sent = sentences[i]
        # If current sentence is very short, merge with next
        if len(sent.strip()) < 2 and i + 1 < len(sentences):
            sentences[i + 1] = sent + sentences[i + 1]
        else:
            merged_sentences.append(sent)
        i += 1
    
    rprint(f"[blue]📊 Japanese split: {len(merged_sentences)} sentences (gap threshold: {gap_threshold}s)[/blue]")
    return merged_sentences

def split_by_mark(nlp):
    whisper_language = load_key("whisper.language")
    language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language # consider force english case
    joiner = get_joiner(language)
    rprint(f"[blue]🔍 Using {language} language joiner: '{joiner}'[/blue]")
    chunks = pd.read_excel("output/log/cleaned_chunks.xlsx")
    
    # Special handling for Japanese - use time-based splitting due to lack of punctuation in ASR
    if language == 'ja':
        sentences_by_mark = split_japanese_by_time_and_grammar(chunks, nlp)
    else:
        # Clean text: remove surrounding quotes and any embedded quotes
        chunks.text = chunks.text.apply(lambda x: str(x).strip('"').strip('"').replace('"', '').strip())
        
        # join with joiner
        input_text = joiner.join(chunks.text.to_list())

        doc = nlp(input_text)
        assert doc.has_annotation("SENT_START")

        # skip - and ...
        sentences_by_mark = []
        current_sentence = []
        
        # iterate all sentences
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
        
        # add the last sentence
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
