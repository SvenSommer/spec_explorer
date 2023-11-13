from data_importer.controller.RequirementComparer import RequirementComparer


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class CosineRequirementComparer(RequirementComparer):
    def calculate_similarity(self, text1: str, text2: str) -> float:
        # Assume TfidfVectorizer and cosine_similarity are imported
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return similarity[0][0]

    def get_comparison_method(self) -> str:
        return 'cosine_similarity'