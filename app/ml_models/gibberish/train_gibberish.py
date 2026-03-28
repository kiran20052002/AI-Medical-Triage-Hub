import pandas as pd
import pickle
import nltk
import string
import os
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Setup NLTK
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
ps = PorterStemmer()
stop_words = set(stopwords.words('english'))
punctuation = set(string.punctuation)

def transform_text(text, remove_stopwords=False):
    text = str(text).lower()
    text = nltk.word_tokenize(text)
    
    y = [i for i in text if i.isalnum()]
    
    # We keep stopwords for Gibberish detection as discussed
    text = [i for i in y if (not remove_stopwords or i not in stop_words) and i not in punctuation]
    
    return " ".join([ps.stem(i) for i in text])

def train_gibberish():
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, "gibberish_data.csv")
    
    print("Loading data...")
    # Using 100k samples for a balance of speed and accuracy
    df = pd.read_csv(data_path, encoding='latin1').sample(100000, random_state=42)
    
    # Standardize columns
    if 'response' in df.columns:
        df = df[['label', 'response']]
    elif 'Response' in df.columns:
        df = df[['Label', 'Response']]
    df.columns = ['target', 'text']
    
    from sklearn.preprocessing import LabelEncoder
    encoder = LabelEncoder()
    df['target'] = encoder.fit_transform(df['target'])
    
    df = df.drop_duplicates(keep='first')
    
    print(f"Processing {len(df)} samples...")
    df['transformed_text'] = df['text'].astype(str).apply(transform_text)
    
    print("Vectorizing...")
    tfidf = TfidfVectorizer(max_features=10000, analyzer='char', ngram_range=(2,3))
    X = tfidf.fit_transform(df['transformed_text'])
    y = df['target'].values
    
    print("Training RandomForest model...")
    model = RandomForestClassifier(n_estimators=50, random_state=2, n_jobs=-1)
    model.fit(X, y)
    
    print("Saving pickles...")
    with open(os.path.join(base_path, "vectorizer.pkl"), 'wb') as f:
        pickle.dump(tfidf, f)
    with open(os.path.join(base_path, "model.pkl"), 'wb') as f:
        pickle.dump(model, f)
    
    print("Retraining complete!")

if __name__ == "__main__":
    train_gibberish()
