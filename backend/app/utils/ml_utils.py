import os
import joblib
import nltk
import string
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer

# Setup NLTK (Download quietly if not available)
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)

ps = PorterStemmer()
try:
    stop_words = set(stopwords.words('english'))
except Exception:
    stop_words = set()
punctuation = set(string.punctuation)

def transform_text(text, remove_stopwords=False):
    """
    Standardize, tokenize, and stem the user query.
    Keeps stopwords for Gibberish detection, removes them for Spam/Medical.
    """
    text = str(text).lower()
    text = nltk.word_tokenize(text)
    
    y = [i for i in text if i.isalnum()]
    text = [i for i in y if (not remove_stopwords or i not in stop_words) and i not in punctuation]
    
    return " ".join([ps.stem(i) for i in text])

# Paths to models
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "ml_models")

SPAM_DIR = os.path.join(MODELS_DIR, "spam")
GIBBERISH_DIR = os.path.join(MODELS_DIR, "gibberish")
MEDICAL_DIR = os.path.join(MODELS_DIR, "medical")

# Global variables for models and vectorizers
spam_model = None
spam_vectorizer = None
gibberish_model = None
gibberish_vectorizer = None
medical_model = None
medical_vectorizer = None

def load_models():
    """Load all 3 models and vectorizers into memory."""
    global spam_model, spam_vectorizer
    global gibberish_model, gibberish_vectorizer
    global medical_model, medical_vectorizer
    
    try:
        # Load Spam Model
        spam_model_path = os.path.join(SPAM_DIR, "model.pkl")
        spam_vect_path = os.path.join(SPAM_DIR, "vectorizer.pkl")
        if os.path.exists(spam_model_path) and os.path.exists(spam_vect_path):
            spam_model = joblib.load(spam_model_path)
            spam_vectorizer = joblib.load(spam_vect_path)
            
        # Load Gibberish Model
        gib_model_path = os.path.join(GIBBERISH_DIR, "model.pkl")
        gib_vect_path = os.path.join(GIBBERISH_DIR, "vectorizer.pkl")
        if os.path.exists(gib_model_path) and os.path.exists(gib_vect_path):
            gibberish_model = joblib.load(gib_model_path)
            gibberish_vectorizer = joblib.load(gib_vect_path)
            
        # Load Medical Model
        med_model_path = os.path.join(MEDICAL_DIR, "model.pkl")
        med_vect_path = os.path.join(MEDICAL_DIR, "vectorizer.pkl")
        if os.path.exists(med_model_path) and os.path.exists(med_vect_path):
            medical_model = joblib.load(med_model_path)
            medical_vectorizer = joblib.load(med_vect_path)
            
    except Exception as e:
        print(f"Error loading ML models: {e}")

async def verify_medical_query(text: str) -> dict:
    """
    3-Stage Pipeline: Spam -> Gibberish -> Medical
    Returns {"is_valid": True/False, "reason": "..."}
    """
    # If models are not loaded, we try to load them
    if spam_model is None or gibberish_model is None or medical_model is None:
        load_models()
        
    # If still not fully loaded, allow by default with a warning to avoid breaking the app
    if spam_model is None or gibberish_model is None or medical_model is None:
        print("Warning: ML Models not fully loaded. Approving query by default.")
        return {"is_valid": True, "reason": "Models unavailable. Defaulting to valid."}
        
    try:
        # Transform the text properly as the models expect
        text_with_stopwords = transform_text(text, remove_stopwords=False)
        text_without_stopwords = transform_text(text, remove_stopwords=True)

        # Stage 1: Spam Detection (1 = Spam, 0 = Normal)
        spam_features = spam_vectorizer.transform([text_without_stopwords])
        is_spam = spam_model.predict(spam_features)[0]
        if is_spam == 1:
            return {"is_valid": False, "reason": "Query blocked: Detected as spam."}
            
        # Stage 2: Gibberish Detection (0 = Gibberish, 1 = Normal)
        gib_features = gibberish_vectorizer.transform([text_with_stopwords])
        is_gibberish = gibberish_model.predict(gib_features)[0]
        if is_gibberish == 0:
            return {"is_valid": False, "reason": "Query blocked: Detected as gibberish."}
            
        # Stage 3: Medical Detection (1 = Medical, 0 = Non-Medical)
        med_features = medical_vectorizer.transform([text_without_stopwords])
        is_medical = medical_model.predict(med_features)[0]
        if is_medical == 0:
            return {"is_valid": False, "reason": "Query blocked: Detected as non-medical."}
            
        return {"is_valid": True, "reason": "Valid medical query."}
        
    except Exception as e:
        print(f"Error in ML pipeline classification: {e}")
        # Default to True on crash
        return {"is_valid": True, "reason": f"Pipeline error: {e}"}

# Attempt initial load 
load_models()
