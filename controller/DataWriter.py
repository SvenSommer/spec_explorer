import sqlite3
from Specification import Specification


class DataWriter:
    def __init__(self, conn, overwrite) -> None:
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.conn.row_factory = self.dict_factory
        self.local_cache = {}
        self.configure_database(overwrite)
        self.populate_static_data()
        self.requirements_to_insert = []
        self.requirement_similarities_to_insert = []

    def get_or_create_id(self, table_name, entity_name):
        if (table_name, entity_name) in self.local_cache:
            return self.local_cache[(table_name, entity_name)]

        self.cursor.execute(
            f"SELECT id FROM {table_name} WHERE name = ?", (entity_name,)
        )
        result = self.cursor.fetchone()

        if result:
            self.local_cache[(table_name, entity_name)] = result[0]
            return result[0]
        else:
            self.cursor.execute(
                f"INSERT INTO {table_name} (name) VALUES (?)", (entity_name,)
            )
            self.conn.commit()
            self.local_cache[(table_name, entity_name)] = self.cursor.lastrowid
            return self.cursor.lastrowid

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def drop_tables(self, tables):
        for table in tables:
            self.cursor.execute(f"DROP TABLE IF EXISTS {table}")

    def configure_database(self, overwrite):
        tables = {
            "specifications": "complex",
            "requirements": "complex",
            "requirement_similarities": "complex",
            "spec_categories": "simple",
            "spec_types": "simple",
            "req_sources": "simple",
            "req_obligations": "simple",
            "comparison_methods": "simple",
            "req_test_procedures": "simple",
        }

        if overwrite:
            self.drop_tables([table for table in tables])

        for table, table_type in tables.items():
            if table_type == "simple":
                self.create_standard_table(table)

        self.create_specifications_table()
        self.create_requirements_table()
        self.create_requirement_similarities_table()
        self.conn.commit()

    def create_specifications_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS specifications (
                id INTEGER PRIMARY KEY,
                name TEXT,
                version TEXT,
                fullname TEXT,
                file_path TEXT,
                category_id INTEGER,
                type_id INTEGER,
                req_count INTEGER,
                status TEXT DEFAULT 'pending',
                UNIQUE(name, version),
                FOREIGN KEY(category_id) REFERENCES spec_categories(id),
                FOREIGN KEY(type_id) REFERENCES spec_types(id)
            )
            """
        )

    def create_requirements_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY,
                specification_id INTEGER,
                source_id INTEGER,
                requirement_number TEXT,
                title TEXT,
                description TEXT,
                processed_title TEXT,
                processed_description TEXT,
                obligation_id INTEGER,
                test_procedure_id INTEGER,
                FOREIGN KEY(specification_id) REFERENCES specifications(id),
                FOREIGN KEY(obligation_id) REFERENCES obligations(id),
                FOREIGN KEY(test_procedure_id) REFERENCES test_procedures(id)
            )
            """
        )

    def create_requirement_similarities_table(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS requirement_similarities (
                combined_identifier TEXT PRIMARY KEY,
                specification1_id INTEGER,
                specification2_id INTEGER,
                requirement1_id INTEGER,
                requirement2_id INTEGER,
                requirement1_number TEXT,
                requirement2_number TEXT,
                title_similarity_score REAL,
                description_similarity_score REAL,
                comparison_method_id INTEGER,
                FOREIGN KEY(requirement1_id) REFERENCES requirements(id),
                FOREIGN KEY(requirement2_id) REFERENCES requirements(id),
                FOREIGN KEY(comparison_method_id) REFERENCES comparison_methods(id)
            )
            """
        )

    def create_standard_table(self, table_name):
        self.cursor.execute(
            f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        )
        """
        )

    def populate_static_data(self):
        static_data = [
            ("Konzepte", "Spezifikationsdokumente"),
            ("Systemlösung", "Spezifikationsdokumente"),
            ("Spezifikationen", "Spezifikationsdokumente"),
            ("Feature-Spezifikationen", "Spezifikationsdokumente"),
            ("Richtlinien", "Spezifikationsdokumente"),
            ("Produkttyp Steckbriefe", "Steckbriefe"),
            ("Anbietertyp Steckbriefe", "Steckbriefe"),
            ("Anwendungssteckbrief", "Steckbriefe"),
            ("Verzeichnis", "Steckbriefe"),
            ("Unbekannt", "Unbekannt"),
        ]

        for type_name, category_name in static_data:
            self.get_or_create_id("spec_categories", category_name)
            self.get_or_create_id("spec_types", type_name)

    def get_or_create_specification(self, parsed_file):
        category_id = self.get_or_create_id(
            "spec_categories", parsed_file.category_type
        )
        type_id = self.get_or_create_id("spec_types", parsed_file.spec_type)
        self.cursor.execute(
            """
            INSERT INTO specifications (name, version, fullname, file_path, category_id, type_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                parsed_file.spec_name,
                parsed_file.spec_version,
                parsed_file.filename,
                parsed_file.file_path,
                category_id,
                type_id,
            ),
        )
        self.conn.commit()

        self.cursor.execute(
            """
            SELECT id FROM specifications
            WHERE name = ? AND version = ?
            """,
            (parsed_file.spec_name, parsed_file.spec_version),
        )
        spec_id = self.cursor.fetchone()
        if spec_id:
            spec_id = spec_id[0]
        else:
            raise Exception(
                f"Specification {parsed_file.spec_name} v{parsed_file.spec_version} could not be retrieved or added to the database."
            )

        spec = Specification(
            spec_id,
            parsed_file.spec_name,
            parsed_file.spec_version,
            parsed_file.filename,
            parsed_file.file_path,
            [],
        )

        return spec

    def update_specification_req_count(self, spec_id):
        """
        Updates the req_count column in the specifications table for a given spec_id.
        The function counts the number of related entries in the requirements table
        and updates the req_count for the specified specification.
        """
        # Count the number of requirements for the given specification ID
        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM requirements
            WHERE specification_id = ?
            """,
            (spec_id,),
        )
        req_count = self.cursor.fetchone()[0]

        # Update the req_count column in the specifications table
        self.cursor.execute(
            """
            UPDATE specifications
            SET req_count = ?
            WHERE id = ?
            """,
            (req_count, spec_id),
        )
        self.conn.commit()

    def add_requirement(self, requirement):
        source_id = self.get_or_create_id("req_sources", requirement.source)
        obligation_id = self.get_or_create_id("req_obligations", requirement.obligation)
        test_procedure_id = self.get_or_create_id(
            "req_test_procedures", requirement.test_procedure
        )

        self.requirements_to_insert.append(
            (
                requirement.specification_id,
                source_id,
                requirement.requirement_number,
                requirement.title,
                requirement.description,
                requirement.processed_title,
                requirement.processed_description,
                obligation_id,
                test_procedure_id,
            )
        )

    def commit_requirements(self):
        self.cursor.executemany(
            """
            INSERT INTO requirements (
                specification_id, source_id, requirement_number, title, description,
                processed_title, processed_description, obligation_id, test_procedure_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self.requirements_to_insert,
        )
        self.requirements_to_insert = []  # Clear the list after inserting
        self.conn.commit()

    def add_requirement_similarities(
        self,
        spec1_id: int,
        spec2_id: int,
        requirement1_id: int,
        requirement2_id: int,
        requirement1_number: str,
        requirement2_number: str,
        title_similarity: float,
        description_similarity: float,
        comparison_method: str,
    ):
        combined_identifier = f"{requirement1_id}_{requirement2_id}"
        title_similarity_rounded = round(title_similarity, 3)
        description_similarity_rounded = round(description_similarity, 3)
        method_id = self.get_or_create_id("comparison_methods", comparison_method)

        self.requirement_similarities_to_insert.append(
            (
                combined_identifier,
                spec1_id,
                spec2_id,
                requirement1_id,
                requirement2_id,
                requirement1_number,
                requirement2_number,
                title_similarity_rounded,
                description_similarity_rounded,
                method_id,
            )
        )

    def commit_requirement_similarities(self):
        try:
            self.cursor.executemany(
                """
                INSERT INTO requirement_similarities (
                    combined_identifier,
                    specification1_id,
                    specification2_id,
                    requirement1_id,
                    requirement2_id,
                    requirement1_number,
                    requirement2_number,
                    title_similarity_score,
                    description_similarity_score,
                    comparison_method_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?,?)
                """,
                self.requirement_similarities_to_insert,
            )
        except sqlite3.IntegrityError as e:
            print(f"An error occurred: {e}")
        self.requirement_similarities_to_insert = []  # Clear the list after inserting
        self.conn.commit()

    def set_specification_status(self, spec_id, status):
        query = """
        UPDATE specifications
        SET status = ?
        WHERE id = ?
        """
        with self.conn:
            self.conn.execute(query, (status, spec_id))

    def close_connection(self):
        """
        Close the database connection.
        """
        self.conn.close()
