import os
import re
import spacy
from PyPDF2 import PdfReader 
from .engine import HybridVectorGraphRag 

def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF file using PyPDF2.

    :param pdf_path: Path to the PDF file.
    :return: Extracted text as a string.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + ' '
        return text.strip()
    except Exception as e:
        print(f"Failed to extract text from PDF {pdf_path}: {e}")
        return ''

def extract_text_from_txt(txt_path):
    """
    Extract text from a TXT file.

    :param txt_path: Path to the TXT file.
    :return: Extracted text as a string.
    """
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        return content
    except Exception as e:
        print(f"Failed to read TXT file {txt_path}: {e}")
        return ''

def load_and_process_file(file_path, nlp):
    """
    Load and process a single file (TXT or PDF).

    :param file_path: Path to the file.
    :param nlp: SpaCy language model.
    :return: Processed text as a string or None if failed.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext == '.txt':
        content = extract_text_from_txt(file_path)
    elif ext == '.pdf':
        content = extract_text_from_pdf(file_path)
    else:
        print(f"Unsupported file format for file {file_path}. Skipping.")
        return None

    if not content:
        print(f"No content extracted from {file_path}. Skipping.")
        return None

    # Step 1: Replace newlines and carriage returns with spaces
    content = content.replace('\n', ' ').replace('\r', ' ')

    # Step 2: Normalize whitespace (replace multiple spaces/tabs with a single space)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\.([A-ZÀ-ÿ])', r'. \1', content)

    try:
        doc = nlp(content)
        sentences = [sent.text.strip() for sent in doc.sents]
        formatted_content = ' '.join(sentences)
    except Exception as e:
        print(f"SpaCy processing failed for {file_path}: {e}")
        formatted_content = content

    print(f"Successfully loaded and formatted corpus from {file_path}.")
    return formatted_content

def hybrid_vector_graph_rag_ingest_corpus():
    """
    Ingest all supported files from the corpus directory.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_dir = os.path.join(current_dir, 'corpus') 

    if not os.path.isdir(corpus_dir):
        print(f"Corpus directory {corpus_dir} does not exist.")
        exit(1)

    # Initialize SpaCy outside the loop for efficiency
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception as e:
        print(f"Failed to load SpaCy model: {e}")
        exit(1)

    rag = HybridVectorGraphRag()

    for filename in os.listdir(corpus_dir):
        file_path = os.path.join(corpus_dir, filename)
        
        if os.path.isfile(file_path):
            print(f"Processing file: {filename}")
            processed_text = load_and_process_file(file_path, nlp)
            
            if processed_text:
                texts = [processed_text] 
                
                try:
                    result = rag.ingest(texts)
                    print(f"Ingestion Result for {filename}:")
                    print(result)
                except Exception as e:
                    print(f"An error occurred during ingestion of {filename}: {e}")
        else:
            print(f"Skipping {filename} as it is not a file.")

