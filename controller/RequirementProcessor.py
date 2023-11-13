import openpyxl
import logging
import os
import re
import sqlite3
import string
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer

from Requirement import Requirement


class RequirementProcessor:
    def __init__(self, data_writer, words_to_replace):
        self.data_writer = data_writer
        self.nlp = spacy.load("de_core_news_md")
        nltk.download("stopwords")
        nltk.download("wordnet")
        self.words_to_replace = words_to_replace

    def preprocess_text(self, text):
        if text is None or text.strip() == "":
            return None

        # Replace each word in the array with an empty string
        for word_to_replace in self.words_to_replace:
            text = text.replace(word_to_replace, "")

        # Continue with the preprocessing steps
        text = text.lower()
        text = text.translate(str.maketrans("", "", string.punctuation))
        text = re.sub(r"\d+", "", text)
        text = text.strip()

        # Tokenization and stopword removal
        stop_words = set(stopwords.words("german"))
        words = text.split()
        words = [word for word in words if word not in stop_words]

        # Stemming
        stemmer = SnowballStemmer("german")
        words = [stemmer.stem(word) for word in words]

        return " ".join(words)

    def import_requirements_to_db(self, specification):
        print(f"Importing {specification.name}")
        workbook = openpyxl.load_workbook(specification.file_path)
        sheet = workbook["Festlegungen"]

        total_entries = 0
        for row in sheet.iter_rows(min_row=2):  # Skip the header row
            requirement_number = row[0].value
            title = row[1].value
            description = row[2].value
            obligation = row[4].value  # Skip 'Beschreibung (HTML)'

            source = specification.name
            test_procedure = "unknown"

            # Check if there are more columns for 'Quelle (Referenz)' and 'Pruefverfahren'
            if len(row) > 5:
                source = row[5].value or source
            if len(row) > 6:
                test_procedure = row[6].value

            processed_title = self.preprocess_text(title)
            processed_description = self.preprocess_text(description)

            if processed_title is None or processed_description is None:
                logging.error(
                    f"Row {total_entries+2} in {specification.fullname} has empty title or description and will be skipped."
                )
                continue

            requirement = Requirement(
                specification_id=specification.id,
                source=source,
                requirement_number=requirement_number,
                title=title,
                description=description,
                processed_title=processed_title,
                processed_description=processed_description,
                obligation=obligation,
                test_procedure=test_procedure,
            )

            try:
                self.data_writer.add_requirement(requirement)
                total_entries += 1
            except sqlite3.Error as e:
                logging.error(f"Error inserting data into database: {e}")
                continue
        self.data_writer.commit_requirements()
        self.data_writer.update_specification_req_count(specification.id)

        logging.info(
            f"Total number of entries added from {specification.name}: {total_entries}"
        )
