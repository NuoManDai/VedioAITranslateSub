import pandas as pd
import json
import concurrent.futures
from core.translate_lines import translate_lines
from core._4_1_summarize import search_things_to_note_in_prompt
from core._8_1_audio_task import check_len_then_trim
from core._6_gen_sub import align_timestamp
from core.utils import *
from rich.console import Console
from difflib import SequenceMatcher
from core.utils.models import *
console = Console()

# Function to split text into chunks
def split_chunks_by_chars(chunk_size, max_i): 
    """Split text into chunks based on character count, return a list of multi-line text chunks"""
    with open(_3_2_SPLIT_BY_MEANING, "r", encoding="utf-8") as file:
        sentences = file.read().strip().split('\n')

    chunks = []
    chunk = ''
    sentence_count = 0
    for sentence in sentences:
        if len(chunk) + len(sentence + '\n') > chunk_size or sentence_count == max_i:
            chunks.append(chunk.strip())
            chunk = sentence + '\n'
            sentence_count = 1
        else:
            chunk += sentence + '\n'
            sentence_count += 1
    chunks.append(chunk.strip())
    return chunks

# Get context from surrounding chunks
def get_previous_content(chunks, chunk_index):
    return None if chunk_index == 0 else chunks[chunk_index - 1].split('\n')[-3:] # Get last 3 lines
def get_after_content(chunks, chunk_index):
    return None if chunk_index == len(chunks) - 1 else chunks[chunk_index + 1].split('\n')[:2] # Get first 2 lines

# 🔍 Translate a single chunk
def translate_chunk(chunk, chunks, theme_prompt, i):
    things_to_note_prompt = search_things_to_note_in_prompt(chunk)
    previous_content_prompt = get_previous_content(chunks, i)
    after_content_prompt = get_after_content(chunks, i)
    translation, english_result, full_result = translate_lines(chunk, previous_content_prompt, after_content_prompt, things_to_note_prompt, theme_prompt, i)
    return i, english_result, translation, full_result

# Add similarity calculation function
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

# 🚀 Main function to translate all chunks
@check_file_exists(_4_2_TRANSLATION)
def translate_all():
    console.print("[bold green]Start Translating All...[/bold green]")
    chunks = split_chunks_by_chars(chunk_size=600, max_i=10)
    with open(_4_1_TERMINOLOGY, 'r', encoding='utf-8') as file:
        theme_prompt = json.load(file).get('theme')

    # Auto-detect CJK mode based on source language
    whisper_language = load_key("whisper.language")
    detected_language = load_key("whisper.detected_language") if whisper_language == 'auto' else whisper_language
    # Support both ISO codes (ja, zh, ko) and full names (japanese, chinese, korean)
    cjk_languages = ['ja', 'zh', 'ko', 'japanese', 'chinese', 'korean']
    use_cjk_mode = detected_language.lower() in cjk_languages
    
    if use_cjk_mode:
        console.print(f"[blue]📝 CJK split mode auto-enabled for language: {detected_language}[/blue]")

    # 🔄 Use concurrent execution for translation
    # Note: Avoid using Rich Progress/Live here as it conflicts with stdout capture in processing_service
    console.print(f"[cyan]Translating {len(chunks)} chunks...[/cyan]")
    with concurrent.futures.ThreadPoolExecutor(max_workers=load_key("max_workers")) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            future = executor.submit(translate_chunk, chunk, chunks, theme_prompt, i)
            futures.append(future)
        results = []
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            completed += 1
            print(f"Progress: {completed}/{len(chunks)} chunks ({100*completed//len(chunks)}%)")

    results.sort(key=lambda x: x[0])  # Sort results based on original order
    
    # 💾 Save translation results to txt file (Origin → Free translation)
    with open(_4_2_TRANSLATION_TXT, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("Translate Expressiveness (Origin → Free)\n")
        f.write("=" * 60 + "\n\n")
        line_num = 1
        for idx, english_result, translation, full_result in results:
            for key, data in full_result.items():
                origin = data.get('origin', '')
                free = data.get('free', data.get('direct', ''))  # fallback to direct if no free
                f.write(f"[{line_num}]  {origin}\n")
                f.write(f"     {free}\n\n")
                line_num += 1
    console.print(f"[green]💾 Translation log saved to → {_4_2_TRANSLATION_TXT}[/green]")
    
    # 💾 Save results to lists and Excel file
    src_text, trans_text = [], []
    
    # Collect origin sentences from LLM results for CJK adjustment
    origin_sentences = []
    if use_cjk_mode:
        for idx, english_result, translation, full_result in results:
            for key, data in full_result.items():
                origin = data.get('origin', '').strip()
                if origin:
                    origin_sentences.append(origin)
        console.print(f"[blue]📝 CJK mode: Collected {len(origin_sentences)} origin sentences from LLM[/blue]")
    
    if use_cjk_mode:
        # CJK mode: Use original split sentences (same as non-CJK)
        # align_timestamp will handle the timestamp alignment
        console.print("[blue]📝 CJK mode: Using NLP split sentences with align_timestamp[/blue]")
    
    # Same logic for both CJK and non-CJK: use NLP split sentences
    for i, chunk in enumerate(chunks):
        chunk_lines = chunk.split('\n')
        src_text.extend(chunk_lines)
        
        # Calculate similarity between current chunk and translation results
        chunk_text = ''.join(chunk_lines).lower()
        matching_results = [(r, similar(''.join(r[1].split('\n')).lower(), chunk_text)) 
                          for r in results]
        best_match = max(matching_results, key=lambda x: x[1])
        
        # Check similarity and handle exceptions
        if best_match[1] < 0.9:
            console.print(f"[yellow]Warning: No matching translation found for chunk {i}[/yellow]")
            raise ValueError(f"Translation matching failed (chunk {i})")
        elif best_match[1] < 1.0:
            console.print(f"[yellow]Warning: Similar match found (chunk {i}, similarity: {best_match[1]:.3f})[/yellow]")
            
        trans_text.extend(best_match[0][2].split('\n'))
    
    # Ensure src_text and trans_text have same length
    if len(src_text) != len(trans_text):
        console.print(f"[yellow]⚠️ Length mismatch: src={len(src_text)}, trans={len(trans_text)}. Adjusting...[/yellow]")
        min_len = min(len(src_text), len(trans_text))
        if len(src_text) > len(trans_text):
            # Pad translation with empty strings
            trans_text.extend([''] * (len(src_text) - len(trans_text)))
        else:
            # Pad source with empty strings
            src_text.extend([''] * (len(trans_text) - len(src_text)))
    
    # Trim long translation text
    df_text = pd.read_excel(_2_CLEANED_CHUNKS)
    df_text['text'] = df_text['text'].str.strip('"').str.strip()
    df_translate = pd.DataFrame({'Source': src_text, 'Translation': trans_text})
    subtitle_output_configs = [('trans_subs_for_audio.srt', ['Translation'])]
    
    # Step 1: Use align_timestamp to get initial timestamps (for both CJK and non-CJK)
    # This uses character matching against the NLP split sentences
    console.print("[blue]📝 Step 1: Using align_timestamp for initial timestamps[/blue]")
    df_time = align_timestamp(df_text, df_translate, subtitle_output_configs, output_dir=None, for_display=False, keep_numeric=True)
    
    if use_cjk_mode and origin_sentences:
        # Step 2: For CJK, adjust timestamps based on LLM's origin sentences
        # This helps correct any ASR single-character timing errors
        console.print("[blue]📝 Step 2: Adjusting timestamps based on LLM origin sentences[/blue]")
        
        try:
            import re
            # Build character-to-word mapping from ASR output
            full_text = ''
            char_to_word_idx = {}
            
            for idx, row in df_text.iterrows():
                word = str(row['text']).strip()
                clean_word = re.sub(r'[^\w]', '', word)
                start_pos = len(full_text)
                full_text += clean_word
                for pos in range(start_pos, len(full_text)):
                    char_to_word_idx[pos] = idx
            
            # For each row, try to find matching origin sentence and adjust timestamps
            adjustments_made = 0
            used_origins = set()  # Track which origins have been used
            
            for i, row in df_time.iterrows():
                src_sentence = str(row['Source']).strip()
                clean_src = re.sub(r'[^\w]', '', src_sentence)
                
                if not clean_src:
                    continue
                
                # Find best matching origin sentence (that hasn't been used yet)
                best_origin = None
                best_similarity = 0.8  # Minimum threshold
                best_origin_idx = -1
                
                for oi, origin in enumerate(origin_sentences):
                    if oi in used_origins:
                        continue
                    clean_origin = re.sub(r'[^\w]', '', origin)
                    sim = similar(clean_src, clean_origin)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_origin = origin
                        best_origin_idx = oi
                
                if best_origin and best_origin_idx >= 0:
                    used_origins.add(best_origin_idx)
                    clean_origin = re.sub(r'[^\w]', '', best_origin)
                    
                    # Search for origin in full_text to get more precise timestamps
                    search_pos = 0
                    while search_pos <= len(full_text) - len(clean_origin):
                        if full_text[search_pos:search_pos + len(clean_origin)] == clean_origin:
                            start_word_idx = char_to_word_idx.get(search_pos, 0)
                            end_word_idx = char_to_word_idx.get(search_pos + len(clean_origin) - 1, len(df_text) - 1)
                            
                            new_start = float(df_text.iloc[start_word_idx]['start'])
                            new_end = float(df_text.iloc[end_word_idx]['end'])
                            
                            old_start = float(row['start'])
                            old_end = float(row['end'])
                            
                            # Adjust if there's a meaningful difference (more than 0.1 second)
                            if abs(new_start - old_start) > 0.1 or abs(new_end - old_end) > 0.1:
                                # Only adjust if the difference is reasonable (within 3 seconds)
                                if abs(new_start - old_start) < 3.0 and abs(new_end - old_end) < 3.0:
                                    df_time.at[i, 'start'] = new_start
                                    df_time.at[i, 'end'] = new_end
                                    df_time.at[i, 'duration'] = new_end - new_start
                                    adjustments_made += 1
                            break
                        search_pos += 1
            
            if adjustments_made > 0:
                console.print(f"[green]✅ CJK: Made {adjustments_made} timestamp adjustments based on LLM origins[/green]")
            else:
                console.print("[blue]📝 CJK: No timestamp adjustments needed[/blue]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️ CJK adjustment failed: {e}, keeping original timestamps[/yellow]")
    
    console.print(df_time)
    # apply check_len_then_trim to df_time['Translation'], only when duration > MIN_TRIM_DURATION.
    df_time['Translation'] = df_time.apply(lambda x: check_len_then_trim(x['Translation'], x['duration']) if x['duration'] > load_key("min_trim_duration") else x['Translation'], axis=1)
    console.print(df_time)
    
    df_time.to_excel(_4_2_TRANSLATION, index=False)
    console.print("[bold green]✅ Translation completed and results saved.[/bold green]")

if __name__ == '__main__':
    translate_all()