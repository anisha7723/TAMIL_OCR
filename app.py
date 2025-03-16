from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import hashlib
import io
from google.cloud import vision
import google.generativeai as genai
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "innate-trees-451903-e9-d1a7269a8fd8.json"

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Google Vision API client
vision_client = vision.ImageAnnotatorClient()

# Set up Gemini AI for text enhancement
genai.configure(api_key="AIzaSyDC67haHDultJ3FW4aFTN_aAgC1nm0wuls")  # Replace with your actual API key

# File to store user-corrected text
FEEDBACK_FILE = "ocr_feedback.json"

# Load corrected text from JSON
def load_feedback():
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Save user corrections to JSON
def save_feedback(image_hash, corrected_text):
    feedback_data = load_feedback()
    feedback_data[image_hash] = corrected_text.strip()

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as file:
        json.dump(feedback_data, file, ensure_ascii=False, indent=4)

# Compute a unique hash for an image
def compute_image_hash(image_path):
    hasher = hashlib.md5()
    with open(image_path, 'rb') as img_file:
        hasher.update(img_file.read())
    return hasher.hexdigest()

# Use Google Vision API to extract text
def detect_text(image_path):
    image_hash = compute_image_hash(image_path)

    # Check if corrected text exists
    feedback_data = load_feedback()
    if image_hash in feedback_data:
        return feedback_data[image_hash], image_hash

    with io.open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = vision_client.document_text_detection(image=image)

    if response.error.message:
        return f"Error: {response.error.message}", image_hash

    extracted_text = response.full_text_annotation.text.strip() if response.full_text_annotation else ""

    # Improve text using Gemini AI
    improved_text = improve_text_with_genai(extracted_text)

    return improved_text, image_hash

@app.route('/refine_text', methods=['POST'])
def refine_text():
    try:
        data = request.json
        text = data.get("text", "")

        if not text.strip():
            return jsonify({"error": "No text provided"}), 400
        
        # Define the prompt dynamically
        prompt = f"""
        don't give any additional data only check and correct the tamil spelling and grammer. nor give any suggestions. 
        it is done for a error correction so additional words are not required. just try to replace words that are incorrect in spellings
        use the entire text to find out the context it can most often be a tamil poem or a place or name so keep that in mind
        {text}
        """

        # Call the AI model directly
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)

        # Extract and return the refined text
        improved_text = response.text.strip() if response.text else text
        return jsonify({"refined_text": improved_text})

    except Exception as e:
        return jsonify({"error": f"AI processing failed: {e}"}), 500

# Improve extracted text using AI
def improve_text_with_genai(text):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(f"Improve the accuracy of this OCR-extracted text:\n{text}")
        return response.text.strip() if response.text else text
    except Exception as e:
        print(f"Error in AI text enhancement: {e}")
        return text

@app.route("/get_suggestions", methods=["POST"])
def get_suggestions():
    """Fetch Tamil word suggestions using Gemini AI."""
    data = request.json
    word = data.get("word", "").strip()

    if not word:
        return jsonify({"error": "Invalid input"}), 400

    try:
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(
    f"இந்த தமிழ் சொல்லுக்கு சரியான மாற்றாக இருக்கக்கூடிய நான்கு தமிழ் சொற்களை வழங்கவும். "
    f"சிறந்த மாற்றங்கள் கிடைக்கவில்லை என்றால், ஒரு கேள்வி ('do you want to change it manually?') என்பதையும் சேர்க்கவும்: {word}"
    f"make sure the words or either context specific or has similar spelling to check the spelling as main purpose of this suggestion box is to correct spelling."
    f"do not give explanation only suggestion of words for correction"
    f"give the words seperate by comma"
)


        print("Gemini AI Response:", response.text)  # ✅ Debugging line
        
        if response.text:
            suggestions = response.text.strip().split(",")[:4]  # ✅ Take only top 4 suggestions
            return jsonify({"suggestions": suggestions})
        else:
            return jsonify({"suggestions": []})  # ✅ Ensure empty response doesn't break frontend

    except Exception as e:
        print("Error:", e)  # ✅ Print error if something goes wrong
        return jsonify({"error": str(e)}), 500


# Home route
@app.route('/')
def index():
    return render_template('extraction.html')

# OCR Extraction Route
@app.route('/extract_text', methods=['POST'])
def extract_text():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
    image.save(image_path)

    try:
        extracted_text, image_hash = detect_text(image_path)
        return jsonify({"text": extracted_text, "image_hash": image_hash})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Save corrected text
@app.route('/save_correction', methods=['POST'])
def save_correction():
    data = request.get_json()
    image_hash = data.get('image_hash', "").strip()
    corrected_text = data.get('corrected_text', "").strip()

    if not image_hash or not corrected_text:
        return jsonify({'error': 'Invalid input'}), 400

    save_feedback(image_hash, corrected_text)
    return jsonify({'message': 'Correction saved successfully'})

@app.route('/word_suggestions', methods=['POST'])
def word_suggestions():
    try:
        data = request.json
        text = data.get("text", "").strip()

        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Example: Generate synonyms or alternative word choices
        prompt = f"""
        Suggest better words for the following text while keeping the original intent:
        
        {text}
        """

        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)

        suggestions = response.text.strip() if response.text else "No suggestions available"
        
        return jsonify({"suggestions": suggestions})

    except Exception as e:
        return jsonify({"error": f"Failed to get word suggestions: {e}"}), 500


# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


if __name__ == '__main__':
    app.run(debug=True)