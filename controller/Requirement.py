
class Requirement:
    specification_id: int  
    source: str
    requirement_number: str
    title: str
    description: str
    processed_title: str
    processed_description: str
    obligation: str
    test_procedure: str = "unknown"  # Default value for test_procedure
    
    def __init__(self, specification_id, source, requirement_number, title, description, 
                 processed_title, processed_description, obligation, test_procedure="unknown"):
        self.specification_id = specification_id
        self.source = source
        self.requirement_number = requirement_number
        self.title = title
        self.description = description
        self.processed_title = processed_title
        self.processed_description = processed_description
        self.obligation = obligation
        self.test_procedure = test_procedure