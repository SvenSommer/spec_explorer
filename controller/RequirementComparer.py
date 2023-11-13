import logging
from abc import ABC, abstractmethod



class RequirementComparer(ABC):
    def __init__(self, data_reader, data_writer, threshold):
        self.data_reader = data_reader
        self.data_writer = data_writer
        self.threshold = threshold


    def compare_requirements(self, specification1, specification2):
        spec1_requirements = self.data_reader.get_requirements_by_specification(specification1)
        spec2_requirements = self.data_reader.get_requirements_by_specification(specification2)
        for i, spec1_req in enumerate(spec1_requirements):
            for spec2_req in spec2_requirements:
                if spec1_req["requirement_number"] == spec2_req["requirement_number"]:
                    continue

                title_similarity = self.calculate_similarity(
                    spec1_req["processed_title"], spec2_req["processed_title"]
                )
                description_similarity = self.calculate_similarity(
                    spec1_req["processed_description"],
                    spec2_req["processed_description"],
                )

                if self.is_above_threshold(description_similarity, self.threshold):
                    self.data_writer.add_requirement_similarities(
                        specification1["id"],
                        specification2["id"],
                        spec1_req["id"],
                        spec2_req["id"],
                        spec1_req["requirement_number"],
                        spec2_req["requirement_number"],
                        title_similarity,
                        description_similarity,
                        self.get_comparison_method()
                    )
            if (i + 1) % 100 == 0:
                logging.info(
                    f"Progress: Compared {i + 1} requirements of {specification1['name']} V{specification1['version']} with {specification2['name']} V{specification2['version']} by using {self.get_comparison_method()}"
                )


    def find_similar_requirements(self, processed_input_text):
        all_requirements = self.data_reader.get_all_requirements()
        
        similar_requirements = []
        
        for req in all_requirements:
            description_similarity = self.calculate_similarity(processed_input_text, req["processed_description"])

            if self.is_above_threshold(description_similarity, self.threshold):
                # Füge Similarität und Threshold dem Requirement-Datenobjekt hinzu
                req_with_similarity = req.copy()  # Erstelle eine Kopie des Requirement-Objekts, falls nötig
                req_with_similarity["similarity"] = description_similarity
                req_with_similarity["threshold"] = self.threshold
                similar_requirements.append(req_with_similarity)

        return similar_requirements

    def is_above_threshold(self, description_similarity: float, treshold: float) -> bool:
        return description_similarity > treshold


    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float:
        pass

    @abstractmethod
    def get_comparison_method(self) -> str:
        pass

