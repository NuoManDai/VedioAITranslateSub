import os
import re
import pandas as pd
import warnings
from core.spacy_utils.load_nlp_model import init_nlp, SPLIT_BY_MARK_FILE
from core.utils.config_utils import load_key, get_joiner
from rich import print as rprint

warnings.filterwarnings("ignore", category=FutureWarning)

def split_japanese_by_punctuation(text):
    """
    Split Japanese text by sentence-ending punctuation marks.
    Handles both Japanese punctuation (。？！) and English punctuation (.?!)
    which may appear in WhisperX output.
    """
    # Pattern to split at sentence-ending punctuation while keeping the punctuation
    # Includes both Japanese (。？！) and English (.?!) punctuation
    # Also handles cases where punctuation might be surrounded by quotes
    pattern = r'([。？！.?!]+)[\s"]*'
    
    parts = re.split(pattern, text)
    sentences = []
    current = ""
    
    for i, part in enumerate(parts):
        if not part:
            continue
        current += part
        # If this part is punctuation (Japanese or English), it's the end of a sentence
        if re.match(r'^[。？！.?!]+$', part):
            if current.strip():
                sentences.append(current.strip())
            current = ""
    
    # Add remaining text if any
    if current.strip():
        sentences.append(current.strip())
    
    return sentences

def split_by_mark(nlp):
    whisper_language = load_key("whisper.language")
    language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language # consider force english case
    joiner = get_joiner(language)
    rprint(f"[blue]🔍 Using {language} language joiner: '{joiner}'[/blue]")
    chunks = pd.read_excel("output/log/cleaned_chunks.xlsx")
    # Clean text: remove surrounding quotes and any embedded quotes
    chunks.text = chunks.text.apply(lambda x: str(x).strip('"').strip('"').replace('"', '').strip())
    
    # join with joiner
    input_text = joiner.join(chunks.text.to_list())
    
    # For Japanese, use custom punctuation-based splitting
    # because spacy may not properly detect sentence boundaries
    if language == 'ja':
        rprint(f"[blue]🇯🇵 Using custom Japanese sentence splitting by punctuation[/blue]")
        sentences_by_mark = split_japanese_by_punctuation(input_text)
        
        # If no sentences were split (no punctuation found), fall back to spacy
        if len(sentences_by_mark) <= 1:
            rprint(f"[yellow]⚠️ No sentence-ending punctuation found, falling back to spacy[/yellow]")
            doc = nlp(input_text)
            sentences_by_mark = [sent.text.strip() for sent in doc.sents]
    else:
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
                    sentences_by_mark.append(' '.join(current_sentence))
                    current_sentence = []
                current_sentence.append(text)
        
        # add the last sentence
        if current_sentence:
            sentences_by_mark.append(' '.join(current_sentence))

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
