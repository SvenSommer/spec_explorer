from typing import Dict, List
import sqlite3

class DataReader:
    def __init__(self, conn):
        self.conn = conn
        self.conn.row_factory = self.dict_factory
        self.cursor = self.conn.cursor()

    def dict_factory(self, cursor, row):
        """
        Create a dictionary from rows in a cursor result.
        The keys will correspond to the column names.
        """
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

    def get_all_requirements(self):
        """
        Retrieve all requirements from the database.
        """
        self.cursor.execute('SELECT * FROM requirements')
        return self.cursor.fetchall()

    def enrich_requirements(self, similar_requirements):
        # Check if the similar_requirements list is empty
        if not similar_requirements:
            print("No similar requirements to process.")
            return []  # Or handle the empty case as appropriate for your application

        # Extract the IDs and similarities into a list of tuples for the WITH clause
        values_list = ", ".join(f"({req['id']}, {req['similarity']})" for req in similar_requirements)
        
        # Prepare the SQL query using a WITH clause to define a temporary table for similarities
        sql_query = f"""
            WITH SimilarityTempTable (id, similarity) AS (
                VALUES {values_list}
            )
            SELECT 
                r.requirement_number as req_requirement_number, 
                spec.name as spec_name,
                source.name AS req_source, 
                r.title AS spec_title, 
                r.description AS spec_description, 
                obligation.name AS spec_obligation, 
                test.name AS spec_test_procedure,
                s.similarity
            FROM 
                requirements r
                JOIN specifications spec ON r.specification_id = spec.id
                JOIN req_sources source ON r.source_id = source.id
                JOIN req_obligations obligation ON r.obligation_id = obligation.id
                JOIN req_test_procedures test ON r.test_procedure_id = test.id
                JOIN SimilarityTempTable s ON r.id = s.id
            WHERE 
                r.id IN ({','.join('?' for _ in similar_requirements)})
            GROUP BY 
                r.requirement_number
            ORDER BY 
                s.similarity DESC
        """

        # Prepare the list of IDs for the parameter substitution
        similar_req_ids = [req["id"] for req in similar_requirements]

        # Execute the query with the list of IDs as the parameter
        try:
            self.cursor.execute(sql_query, similar_req_ids)
        except sqlite3.OperationalError as e:
            print(f"An error occurred: {e}")
            print("SQL query:", sql_query)
            print("Parameters:", similar_req_ids)
            raise

        # Fetch all results
        return self.cursor.fetchall()


        
    
    def get_requirements_by_specification(self, specification) -> List[Dict]:
        """
        Fetch requirements for a given spec_name and spec_version.
        """
        self.cursor.execute(
            '''
            SELECT r.*, s.name, s.version, s.fullname, s.file_path 
            FROM requirements r 
            JOIN specifications s ON r.specification_id = s.id 
            WHERE s.id=? 
            ''', 
            (specification['id'],)
        )
        return self.cursor.fetchall()

    def get_similarities_by_specifiaction(self, specification) -> List[Dict]:
        self.cursor.execute(
            '''		
		SELECT 
        r1.requirement_number as req1_requirement_number,
        source1.name AS req1_source, 
        r1.title AS spec1_title, 
        r1.description AS spec1_description, 
        obligation1.name AS spec1_obligation, 
        test1.name AS spec1_test_procedure,
        r2.requirement_number as req2_requirement_number,
        r2.title AS spec2_title, 
        r2.description AS spec2_description, 
        source2.name AS req2_source, 
        obligation2.name AS spec2_obligation, 
        test2.name AS spec2_test_procedure,
        rs.comparison_method_id as comparison_method,
        rs.title_similarity_score,
        rs.description_similarity_score,
        rs.combined_identifier
      FROM 
        requirement_similarities rs
      JOIN 
        requirements r1 ON rs.requirement1_id = r1.id
      JOIN 
        requirements r2 ON rs.requirement2_id = r2.id
      JOIN 
        specifications s1 ON r1.specification_id = s1.id
		JOIN 
        specifications s2 ON r2.specification_id = s2.id
		JOIN
        req_sources source1 ON r1.source_id = source1.id
      JOIN 
        req_sources source2 ON r2.source_id = source2.id
      JOIN 
        req_obligations obligation1 ON r1.obligation_id = obligation1.id
      JOIN 
        req_obligations obligation2 ON r2.obligation_id = obligation2.id
      JOIN 
        req_test_procedures test1 ON r1.test_procedure_id = test1.id
      JOIN 
        req_test_procedures test2 ON r2.test_procedure_id = test2.id
      WHERE 
        r1.specification_id = ?
		OR
		  r2.specification_id = ?
		
            ''', 
            (specification['id'],)
        )
        return self.cursor.fetchall()

    def get_requirement_by_number(self, requirement_number):
        """
        Retrieve a specific requirement by its number.
        """
        self.cursor.execute(
            '''
            SELECT r.*, s.name, s.version, s.fullname, s.file_path 
            FROM requirements r 
            JOIN specifications s ON r.specification_id = s.id 
            WHERE r.requirement_number = ? 
            ''', 
            (requirement_number,)
        )
        return self.cursor.fetchone()

    def search_requirements(self, search_query):
        """
        Search for requirements that match a search query in their title or description.
        """
        search_query = f'%{search_query}%'
        self.cursor.execute('SELECT * FROM requirements WHERE title LIKE ? OR description LIKE ?', (search_query, search_query))
        return self.cursor.fetchall()
    
    def get_all_specifications(self):
        """
        Retrieve all specifications from the database along with the count of associated requirements,
        including the type, category, and their respective IDs.
        """
        self.cursor.execute(
            '''
            SELECT s.*, t.name AS type, c.name AS category, t.id AS type_id, c.id AS category_id, COUNT(r.specification_id) as requirement_count
            FROM specifications s
            LEFT JOIN requirements r ON s.id = r.specification_id
            LEFT JOIN spec_types t ON s.type_id = t.id
            LEFT JOIN spec_categories c ON s.category_id = c.id
            GROUP BY s.id
            '''
        )
        return self.cursor.fetchall()

    
    def get_similarity_counts(self):
        """
        Retrieve the count of similar requirements between each pair of specifications.
        """
        self.cursor.execute(
            '''
           SELECT 
                r1.specification_id AS spec1_id, 
                r2.specification_id AS spec2_id, 
                s1.name AS spec1_name, 
                s1.version AS spec1_version, 
                s2.name AS spec2_name, 
                s2.version AS spec2_version, 
                COUNT(*) AS similarity_count
            FROM 
                requirement_similarities rs
            JOIN 
                requirements r1 ON rs.requirement1_id = r1.id
            JOIN 
                requirements r2 ON rs.requirement2_id = r2.id
            JOIN 
                specifications s1 ON r1.specification_id = s1.id
            JOIN 
                specifications s2 ON r2.specification_id = s2.id
            GROUP BY 
                r1.specification_id, r2.specification_id;

            '''
        )
        return self.cursor.fetchall()


    def close_connection(self):
        """
        Close the database connection.
        """
        self.conn.close()