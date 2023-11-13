from RequirementComparer import RequirementComparer


class CustomRequirementComparer(RequirementComparer):
    def calculate_similarity(self, text1: str, text2: str) -> float:
        words_text1 = set(text1.split())
        words_text2 = set(text2.split())
        common_words = words_text1.intersection(words_text2)
        total_words = words_text1.union(words_text2)
        return float(len(common_words)) / len(total_words)

    def get_comparison_method(self) -> str:
        return 'custom_similarity'