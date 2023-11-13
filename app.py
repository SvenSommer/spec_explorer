from flask import Flask, request, jsonify, send_from_directory
import logging
import sqlite3
import os
import sys
sys.path.append("./controller")
from RequirementProcessor import RequirementProcessor
from DataReader import DataReader
from DataWriter import DataWriter
from CustomRequirementComparer import CustomRequirementComparer
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/style.css')
def style():
    return send_from_directory('public', 'style.css')

@app.route('/find_similar_requirements', methods=['POST'])
def find_similar_requirements():
    try:
        input_text = request.form.get('initialText')
        if not input_text:
            return jsonify({"error": "Missing input text"}), 400

        db_directory = "./public/db"
        db_file = "requirements.db"
        db_path = os.path.join(db_directory, db_file)
        conn = sqlite3.connect(db_path)
        db_writer = DataWriter(conn, False)
        db_reader = DataReader(conn)

        custom_comparer = CustomRequirementComparer(db_reader, db_writer, 0.2)
        words_to_replace = ["ePA-Frontend", "ePA Frontend",  "E-Rezept-FdV","TI-ITSM-Teilnehmer", "Hersteller", "Produkttyp"]
        processor = RequirementProcessor(db_writer, words_to_replace)

        processed_input_text = processor.preprocess_text(input_text)
        similar_requirements = custom_comparer.find_similar_requirements(processed_input_text)
        print(similar_requirements)
        enriched_similar_requirements = db_reader.enrich_requirements(similar_requirements)
        res = jsonify(enriched_similar_requirements)
        return res

    except Exception as e:
        logging.error("An error occurred", exc_info=True)
        return jsonify({"error": "An error occurred"}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)  # Running on http://127.0.0.1:5000/
