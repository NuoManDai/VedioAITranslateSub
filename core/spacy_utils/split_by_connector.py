import os
import warnings
from core.spacy_utils.load_nlp_model import init_nlp, SPLIT_BY_COMMA_FILE, SPLIT_BY_CONNECTOR_FILE
from core.utils import rprint

warnings.filterwarnings("ignore", category=FutureWarning)

def analyze_connectors(doc, token):
    """
    Analyze whether a token is a connector that should trigger a sentence split.
    
    Processing logic and order:
     1. Check if the token is one of the target connectors based on the language.
     2. For 'that' (English), check if it's part of a contraction (e.g., that's, that'll).
     3. For all connectors, check if they function as a specific dependency of a verb or noun.
     4. Default to splitting for certain connectors if no other conditions are met.
     5. For coordinating conjunctions, check if they connect two independent clauses.
    """
    lang = doc.lang_
    if lang == "en":
        connectors = [
            # 因果
            "because", "since", "therefore", "thus", "hence", "so",
            # 转折
            "but", "however", "although", "though", "yet", "while", "whereas",
            # 并列
            "and", "or", "also", "moreover", "furthermore", "besides",
            # 关系
            "that", "which", "where", "when", "who", "whom", "whose",
            # 条件
            "if", "unless", "provided",
            # 让步
            "even", "despite",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "zh":
        connectors = [
            # 因果
            "因为", "所以", "因此", "故而", "于是", "由于",
            # 转折
            "但是", "然而", "不过", "可是", "却", "但",
            # 并列
            "而且", "并且", "同时", "另外", "此外", "还有",
            # 条件
            "如果", "假如", "要是", "倘若", "若是", "万一",
            # 让步
            "虽然", "尽管", "即使", "哪怕", "纵然", "就算",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "ja":
        connectors = [
            # 逆接 (转折)
            "けれども", "けれど", "けど", "しかし", "だが", "でも", "が", 
            "ところが", "にもかかわらず", "それでも", "ただし", "もっとも",
            # 因果
            "だから", "それで", "ので", "から", "ため", "したがって", 
            "そのため", "よって", "ゆえに", "なぜなら",
            # 并列/添加
            "そして", "また", "さらに", "それから", "および", "かつ", 
            "しかも", "その上", "加えて",
            # 条件
            "なら", "ならば", "たら", "れば", "と", "もし",
            # 让步
            "のに", "ても", "といっても", "にしても",
            # 时间
            "とき", "ときに", "際に", "あと", "まえ",
        ]
        mark_dep = "mark"
        det_pron_deps = ["case"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "fr":
        connectors = [
            # 因果
            "parce que", "car", "donc", "ainsi", "puisque",
            # 转折
            "mais", "cependant", "pourtant", "toutefois", "néanmoins",
            # 并列
            "et", "ou", "aussi", "de plus", "en outre",
            # 关系
            "que", "qui", "où", "quand", "dont", "lequel",
            # 条件
            "si", "pourvu que", "à condition que",
            # 让步
            "bien que", "quoique", "même si",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "ru":
        connectors = [
            # 因果
            "потому что", "поэтому", "так как", "ведь", "ибо",
            # 转折
            "но", "однако", "хотя", "впрочем", "зато",
            # 并列
            "и", "или", "также", "кроме того", "притом",
            # 关系
            "что", "который", "где", "когда", "чей",
            # 条件
            "если", "при условии",
            # 让步
            "несмотря на", "хотя", "даже если",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "es":
        connectors = [
            # 因果
            "porque", "por eso", "así que", "ya que", "puesto que",
            # 转折
            "pero", "sin embargo", "aunque", "no obstante",
            # 并列
            "y", "o", "también", "además", "asimismo",
            # 关系
            "que", "cual", "donde", "cuando", "quien", "cuyo",
            # 条件
            "si", "a menos que", "con tal de que",
            # 让步
            "aunque", "a pesar de que", "si bien",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "de":
        connectors = [
            # 因果
            "weil", "denn", "deshalb", "daher", "darum",
            # 转折
            "aber", "jedoch", "obwohl", "trotzdem", "dennoch",
            # 并列
            "und", "oder", "auch", "außerdem", "ferner",
            # 关系
            "dass", "welche", "wo", "wann", "wer", "dessen",
            # 条件
            "wenn", "falls", "sofern",
            # 让步
            "obwohl", "obgleich", "selbst wenn",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    elif lang == "it":
        connectors = [
            # 因果
            "perché", "quindi", "perciò", "poiché", "siccome",
            # 转折
            "ma", "però", "tuttavia", "sebbene", "benché",
            # 并列
            "e", "o", "anche", "inoltre", "pure",
            # 关系
            "che", "quale", "dove", "quando", "chi", "cui",
            # 条件
            "se", "qualora", "purché",
            # 让步
            "anche se", "nonostante", "malgrado",
        ]
        mark_dep = "mark"
        det_pron_deps = ["det", "pron"]
        verb_pos = "VERB"
        noun_pos = ["NOUN", "PROPN"]
    else:
        return False, False
    
    if token.text.lower() not in connectors:
        return False, False
    
    if lang == "en" and token.text.lower() == "that":
        if token.dep_ == mark_dep and token.head.pos_ == verb_pos:
            return True, False
        else:
            return False, False
    elif token.dep_ in det_pron_deps and token.head.pos_ in noun_pos:
        return False, False
    else:
        return True, False

def split_by_connectors(text, context_words=5, nlp=None):
    doc = nlp(text)
    sentences = [doc.text]  # init
    
    while True:
        # Handle each task with a single cut
        # avoiding the fragmentation of a sentence into multiple parts at the same time.
        split_occurred = False
        new_sentences = []
        
        for sent in sentences:
            doc = nlp(sent)
            start = 0
            
            for i, token in enumerate(doc):
                split_before, _ = analyze_connectors(doc, token)
                
                if i + 1 < len(doc) and doc[i + 1].text in ["'s", "'re", "'ve", "'ll", "'d"]:
                    continue
                
                left_words = doc[max(0, token.i - context_words):token.i]
                right_words = doc[token.i+1:min(len(doc), token.i + context_words + 1)]
                
                left_words = [word.text for word in left_words if not word.is_punct]
                right_words = [word.text for word in right_words if not word.is_punct]
                
                if len(left_words) >= context_words and len(right_words) >= context_words and split_before:
                    rprint(f"[yellow]✂️  Split before '{token.text}': {' '.join(left_words)}| {token.text} {' '.join(right_words)}[/yellow]")
                    new_sentences.append(doc[start:token.i].text.strip())
                    start = token.i
                    split_occurred = True
                    break
            
            if start < len(doc):
                new_sentences.append(doc[start:].text.strip())
        
        if not split_occurred:
            break
        
        sentences = new_sentences
    
    return sentences

def split_sentences_main(nlp):
    # Read input sentences
    with open(SPLIT_BY_COMMA_FILE, "r", encoding="utf-8") as input_file:
        sentences = input_file.readlines()
    
    all_split_sentences = []
    # Process each input sentence
    for sentence in sentences:
        split_sentences = split_by_connectors(sentence.strip(), nlp = nlp)
        all_split_sentences.extend(split_sentences)
    
    with open(SPLIT_BY_CONNECTOR_FILE, "w+", encoding="utf-8") as output_file:
        for sentence in all_split_sentences:
            output_file.write(sentence + "\n")
        # do not add a newline at the end of the file
        output_file.seek(output_file.tell() - 1, os.SEEK_SET)
        output_file.truncate()

    # 保留中间文件用于调试
    # os.remove(SPLIT_BY_COMMA_FILE)
    
    rprint(f"[green]💾 Sentences split by connectors saved to →  `{SPLIT_BY_CONNECTOR_FILE}`[/green]")

if __name__ == "__main__":
    nlp = init_nlp()
    split_sentences_main(nlp)
    # nlp = init_nlp()
    # a = "and show the specific differences that make a difference between a breakaway that results in a goal in the NHL versus one that doesn't."
    # print(split_by_connectors(a, nlp))