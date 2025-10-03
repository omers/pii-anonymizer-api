#!/usr/bin/env python3
"""
Script to install spaCy language model with fallback options.
This handles the common issue where spacy download fails.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and return True if successful."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - Failed: {e.stderr}")
        return False

def install_spacy_model():
    """Install spaCy English model with multiple fallback methods."""
    
    print("🚀 Installing spaCy English language model...")
    
    # Method 1: Standard spacy download
    if run_command("python -m spacy download en_core_web_lg", "Method 1: spacy download"):
        return True
    
    # Method 2: Direct pip install from GitHub
    model_url = "https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.6.0/en_core_web_lg-3.6.0-py3-none-any.whl"
    if run_command(f"pip install {model_url}", "Method 2: Direct pip install"):
        return True
    
    # Method 3: Try smaller model as fallback
    print("⚠️  Large model failed, trying medium model as fallback...")
    if run_command("python -m spacy download en_core_web_md", "Method 3: Fallback to medium model"):
        print("⚠️  Using medium model instead of large. Performance may be slightly reduced.")
        return True
    
    # Method 4: Try small model as last resort
    print("⚠️  Medium model failed, trying small model as last resort...")
    if run_command("python -m spacy download en_core_web_sm", "Method 4: Fallback to small model"):
        print("⚠️  Using small model instead of large. Performance will be reduced.")
        return True
    
    print("❌ All methods failed. Please check your internet connection and try again.")
    return False

def verify_installation():
    """Verify that the spaCy model is properly installed."""
    print("🔍 Verifying installation...")
    
    try:
        import spacy
        
        # Try to load the large model first
        for model_name in ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]:
            try:
                nlp = spacy.load(model_name)
                print(f"✅ Successfully loaded {model_name}")
                
                # Test the model
                doc = nlp("John Doe works at Microsoft.")
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                print(f"✅ Model test successful. Found entities: {entities}")
                return True
            except OSError:
                print(f"⚠️  {model_name} not found, trying next...")
                continue
        
        print("❌ No spaCy English model found.")
        return False
        
    except ImportError:
        print("❌ spaCy not installed.")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 spaCy Model Installation Script")
    print("=" * 60)
    
    if install_spacy_model():
        if verify_installation():
            print("\n🎉 spaCy model installation completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Installation completed but verification failed.")
            sys.exit(1)
    else:
        print("\n❌ Failed to install spaCy model.")
        print("\n💡 Manual installation options:")
        print("1. pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.6.0/en_core_web_lg-3.6.0-py3-none-any.whl")
        print("2. python -m spacy download en_core_web_md  # Medium model")
        print("3. python -m spacy download en_core_web_sm  # Small model")
        sys.exit(1)
