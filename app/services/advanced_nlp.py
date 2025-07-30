import os
from typing import Dict, List, Any, Optional

try:
    import torch
    from transformers import pipeline, AutoTokenizer, AutoModel
    TRANSFORMERS_AVAILABLE = True
    TORCH_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    TORCH_AVAILABLE = False
    torch = None

class AdvancedNLPProcessor:
    """Advanced NLP processor using transformer models with graceful fallbacks"""
    
    def __init__(self):
        self.models_loaded = False
        self.ner_pipeline = None
        self.summarizer = None
        self.classifier = None
        
        if not TRANSFORMERS_AVAILABLE or not TORCH_AVAILABLE:
            print("Transformers/Torch libraries not available, advanced NLP features disabled")
            self.device = "cpu"
            return
            
        self.device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
        
        try:
            self._load_models()
            self.models_loaded = True
            print(f"Advanced NLP models loaded successfully on {self.device}")
        except Exception as e:
            print(f"Advanced NLP models failed to load: {e}")
            self.models_loaded = False
    
    def _load_models(self):
        """Load transformer models"""
        try:
            self.ner_pipeline = pipeline(
                "ner", 
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                device=0 if self.device == "cuda" else -1,
                aggregation_strategy="simple"
            )
            print("NER pipeline loaded successfully")
        except Exception as e:
            print(f"Failed to load NER pipeline: {e}")
            
        try:
            self.summarizer = pipeline(
                "summarization", 
                model="facebook/bart-large-cnn",
                device=0 if self.device == "cuda" else -1
            )
            print("Summarizer pipeline loaded successfully")
        except Exception as e:
            print(f"Failed to load summarizer pipeline: {e}")
            
        try:
            self.classifier = pipeline(
                "text-classification", 
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=0 if self.device == "cuda" else -1
            )
            print("Classifier pipeline loaded successfully")
        except Exception as e:
            print(f"Failed to load classifier pipeline: {e}")
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities using BERT NER"""
        if not self.models_loaded or not self.ner_pipeline:
            return []
        
        try:
            entities = self.ner_pipeline(text)
            return [
                {
                    'text': entity['word'],
                    'label': entity['entity_group'],
                    'confidence': entity['score'],
                    'start': entity['start'],
                    'end': entity['end']
                }
                for entity in entities
            ]
        except Exception as e:
            print(f"NER extraction failed: {e}")
            return []
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 30) -> Optional[str]:
        """Generate text summary using BART"""
        if not self.models_loaded or not self.summarizer:
            return None
            
        try:
            if len(text.split()) < min_length:
                return text
                
            summary = self.summarizer(
                text, 
                max_length=max_length, 
                min_length=min_length, 
                do_sample=False
            )
            return summary[0]['summary_text']
        except Exception as e:
            print(f"Text summarization failed: {e}")
            return None
    
    def classify_sentiment(self, text: str) -> Optional[Dict[str, Any]]:
        """Classify text sentiment"""
        if not self.models_loaded or not self.classifier:
            return None
            
        try:
            result = self.classifier(text)
            return {
                'label': result[0]['label'],
                'confidence': result[0]['score']
            }
        except Exception as e:
            print(f"Sentiment classification failed: {e}")
            return None
    
    def enhance_extraction_results(self, text: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance extraction results with advanced NLP analysis"""
        enhanced_data = extracted_data.copy()
        
        entities = self.extract_entities(text)
        if entities:
            enhanced_data['entities'] = entities
            
        summary = self.summarize_text(text)
        if summary:
            enhanced_data['summary'] = summary
            
        sentiment = self.classify_sentiment(text)
        if sentiment:
            enhanced_data['sentiment'] = sentiment
            
        enhanced_data['advanced_nlp_used'] = self.models_loaded
        
        return enhanced_data
