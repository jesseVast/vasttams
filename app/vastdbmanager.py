'''
vastdbmanager.py
Connect and manage vastdb connection, schema and tables.
'''
import logging
from ibis import _
import vastdb
import vastdb.transaction
import vastdb.table
import pyarrow as pa
from traceback import print_exception

# Logger setup
logger = logging.getLogger(__name__)

class Vastdbmanager:
    '''
    Vastdbmanager(endpoint: str,access_key: str,secret_key: str,bucket: str,schema: str)
    Create a vastdb manager instance to manage connections into a vastdb
    '''
    def __init__(self,
                 endpoint: str,
                 access_key: str,
                 secret_key: str,
                 bucket: str,
                 schema: str
                 ):
        '''
        Vastdbmanager(endpoint: str,access_key: str,secret_key: str,bucket: str)
        '''
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.dbschema=schema
        self.tableschema = {}
        self._ready = False

        logger.info(f"Intialized DB with {endpoint} {access_key} {bucket}")
        self._session = vastdb.connect(endpoint=self.endpoint,
                                 access=self.access_key,
                                 secret=self.secret_key,
                                 timeout=30)
        # setup schema if not existing, then gather the table information.
        self.setup_schema()


    @property
    def session(self):
        return self._session
    
    
    @property
    def tables(self):
        return list(self.tableschema.keys())
    
    
    def create_table(self,tablename: str, tableschema: pa.schema) -> None:
        '''
        create_table(self,tablename: str, tableschema: pa.schema) -> None
        Creates table "tablename" if does not exist.
        Returns: None
        '''
        logger.info(f"Checking table {tablename} exists.")
        with self._session.transaction() as tx:
            # connect to bucket
            bucket=tx.bucket(self.bucket)
            schema = bucket.schema(self.dbschema,fail_if_missing=False)
            # Check if table exists
            table = schema.table(tablename, fail_if_missing=False)
            if table is None:
                table = schema.create_table(tablename, tableschema)
                logger.info(f"Table '{tablename}' created with schema {tableschema}")
            else:
                logger.warning(f"Table '{tablename}' already exists")
            self.tableschema[tablename] = tableschema


    def get_table(self,transaction: vastdb.transaction.Transaction, tablename:str) -> vastdb.table.Table|None:
        '''
        get_table(self,transaction: vastdb.transaction.Transaction,schemaname: str, tablename:str) -> vastdb.table.Table|None:
        Get the tablename for the transaction.
        Return: vastdb.Table|None
        '''
        if tablename in self.tableschema.keys():
            return transaction.bucket(self.bucket).schema(self.dbschema).table(tablename)
        else:
            logger.error(f'Tablename "{tablename}" not initialized. Did you run define_table?')
            raise(Exception(f'Tablename "{tablename}" not initialized. Did you run define_table?'))  


    def _discover_tables(self):
        '''
        _discover_tables() -> None
        For existing schema, discover and pupulate all the table information.
        Return: None
        '''
        with self._session.transaction() as tx:
            # connect to bucket
            schema=tx.bucket(self.bucket).schema(self.dbschema)
            # get list of tables and get their columns.
            for table in schema.tables():
                table_name = table.name
                # get the schema
                self.tableschema[table_name] = table.columns()
                logger.info(f"Table: {table_name} schema is \n{self.tableschema[table_name]}")


    def setup_schema(self) -> None:
        '''
        setup_schema() -> None
        Creates schema if does not already exists. R
        Return: None
        '''
        with self._session.transaction() as tx:
            # connect to bucket
            bucket=tx.bucket(self.bucket)
            # Ensure the schema exists
            try:
                schema = bucket.schema(self.dbschema, fail_if_missing=False)
                if schema is None:
                    schema = bucket.create_schema(self.dbschema)
                    logger.info(f"Schema '{self.dbschema}' created.")
                else:
                    logger.info(f"Schema '{self.dbschema}' already exists")
                    self._discover_tables()
            except Exception as e:
                logger.error(f"Error checking schema due to {print_exception(e)}")
                raise(e)
        self._ready=True
        logger.info("DB is ready.")


    def list_tables(self) -> list:
        '''
        list_tables() -> list
        List tables in the schema
        Return: list
        '''
        with self._session.transaction() as tx:
            schema=tx.bucket(self.bucket).schema(self.dbschema)
            tables = schema.tables()
            logger.info(f"Tables Names: {tables}")
            return tables


    def list_schemas(self) -> list:
        '''
        list_schemas() -> list
        List schemas in database
        Return: list
        '''
        with self._session.transaction() as tx:
            bucket = tx.bucket(self.bucket)
            schemas = bucket.schemas()
            logger.info(f"Schemas in {self.bucket}: {schemas}")
            return schemas
    

    def drop_schema(self) -> None:
        '''
        drop_schema() -> None
        Drop previously defined schema.
        Return: None
        '''
        logger.info(f"Dropping schema {self.dbschema}")
        # first drop all tables in schema
        # So schema exists
        with self._session.transaction() as tx:
            schema = tx.bucket(self.bucket).schema(self.dbschema)
            try:
                schema.drop()
                logger.info(f'Dropped Schema {self.dbschema}')
            except Exception as e:
                logger.error(f'Error dropping Schema {self.dbschema} due to {print_exception(e)}')
                raise(e)
        # clean upp tableschema dictionary
        self.tableschema = {}

        
    def get_table_stats(self,tablename: str) -> list:
        '''
        get_table_stats(tablename: str) -> list
        Get stats on the given table.
        Return: list
        '''
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                stats = table.get_stats()
            logger.debug(f'Table stats for {tablename} - {stats}')
            return stats
        except Exception as e:
            logger.error(f"Get table stats due to {print_exception(e)}")
            raise(e)
    

    def drop_table(self,tablename: str) -> None:
        '''
        drop_table(tablename: str) -> None
        Drop tablename from schema
        Return: None
        '''
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                table.drop()
            logger.info(f'Table {tablename} has been dropped.')
        except Exception as e:
            logger.error(f"Drop failed due to {print_exception(e)}")
            raise(e)


    def get_table_columns(self, tablename: str) -> pa.schema:
        '''
        get_table_columns(tablename)-> pyarrow.schema
        Get the column definitions for the tablename.
        Return: pyarrow.schema
        '''
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                columns = table.columns()
            logger.debug(f'Table columns for {tablename} - {columns}')
            return columns
        except Exception as e:
            logger.error(f"Get table columns failed due to {print_exception(e)}")
            raise(e)
        

    def _select(self, tablename: str, column_names: list|None=None, predicate:str|None=None, internal_rowid: bool=False) -> pa.Table:
        '''
        _select(tablename: str, column_names: list|None, predicate:str="", internal_rowid: bool=False) -> pyarrow.Table
        Select and return rows from tablename based on predicate as pa.Table object
            Predicate needs be in format used by vastdb (Ibis construct)
            $row_id will be returned as a column if internal_rowid=True
        Note: This function is unsuitable for queries returning large amounts of data. Use the vastdb SDK to directly query the table using the session from this class.
        Return:  pyarrow.Table
        '''
        logger.info(f"Tablename: {tablename} Columns: {column_names} Predicate: {predicate} internal_rowid: {internal_rowid}")
        with self._session.transaction() as tx:   
            try:
                table = self.get_table(tx,tablename)
                data=table.select(columns=column_names,predicate=predicate,internal_row_id=internal_rowid)
                pyarrow_table = data.read_all()
                logger.info(f"Returned {len(pyarrow_table)} rows.")
            except Exception as e:
                logger.error(f"Select failed due to {print_exception(e)}")
                raise(e)
        return pyarrow_table
    
    
    def select(self, tablename: str, column_names: list|None=None, predicate:str|None=None, internal_rowid: bool=False,output_by_row=True) -> list:
        '''
        select(tablename: str, column_names: list|None, predicate:str="", internal_rowid: bool=False,output_by_row=True) -> list
            Select and return rows from tablename based on predicate as python list. 
            Predicate needs be in the format used by vastdb.
            $row_id will be returned as a column if internal_rowid=True
            If output_by_row=True, then the result if returned as pylist, else returned as pydict. pylist if useful if processing by rows, 
            pydict is useful for processing by columns.
        Note: This function is unsuitable for queries returning large amounts of data. Use the vastdb SDK to directly query the table using the session from this class.
        Return: list
        '''
        logger.debug(f"Tablename: {tablename} Columns: {column_names} Predicate: {predicate} internal_rowid: {internal_rowid}")
        pyarrow_table = self._select(tablename=tablename,
                                column_names=column_names,
                                predicate=predicate,
                                internal_rowid=internal_rowid)
        if output_by_row:
            return pyarrow_table.to_pylist()
        else:
            return pyarrow_table.to_pydict()
        

    def _get_smallest_column(self,tablename) -> str:
        '''
        _get_smallest_column(tablename) -> str
        Return the name of the column with the smallest byte width. If none is found, return the first column. 
        Return: str
        '''
        first=True
        lowest=None
        for field in self.tableschema[tablename]:
            if first:
                # check if the column is fixed width
                try:
                    u = field.type.byte_width
                    lowest=field
                    first=False
                except:
                    pass
            else:
                try:
                    if lowest.type.byte_width > field.type.byte_width:
                        lowest=field
                except:
                    pass
        if not first:
            logger.info(f"Smallest column is fixed width: {lowest.name}")
            return lowest.name
        else:
            # NO fixed width columns so choose the first column
            logger.info(f"No fixed width column in schema. Returning first column. {self.tableschema[tablename][0].name}")
            return self.tableschema[tablename][0].name


    def delete(self,tablename: str,predicate: str) -> int:
        '''
        delete(tablename: str,predicate: str) -> int:
        Deletes the rows defined by the predicate. Return number of rows deleted. 
        Predicate should not include $row_id column. 
        Return: int
        '''
        logging.info(f'Deleting rows from {tablename} matching predicate {predicate}')
        #Get the row_ids;

        try:
            # Optimization: Get column with the lowest memory cost so we don't need to fetch the whole row. 
            columns = [self._get_smallest_column(tablename=tablename)]
            # Get the row ids and we want to process the whole $row_id column. Need internal_rowid=True.
            pyarrow_table = self._select(tablename=tablename,column_names=columns, predicate=predicate,internal_rowid=True)
        except Exception as e:
            logger.error(f"Select row_ids failed due to {print_exception(e)}")
            raise(e)
        # Now delete the rows
        if len(pyarrow_table) == 0:
            logger.info("No rows to delete.")
            return 0
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                # delete rows.
                table.delete(pyarrow_table)
        except Exception as e:
            logger.error(f"Delete failed due to {print_exception(e)}")
            raise(e)
        logger.info(f"Rows deleted : {len(pyarrow_table)}")
        return len(pyarrow_table)
    
    def delete_rowids(self,tablename: str,delete_rows: pa.Table) -> int:
        '''
        delete_rowids(self,tablename: str,delete_rows: pa.Table) -> int:
        Deletes the rows defined by the internal_rowids. Return number of rows deleted. 
        Return: int
        '''
        logging.info(f'Deleting rows from {tablename} matching predicate {delete_rows.to_pylist()}') 
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                # delete rows.
                table.delete(delete_rows)
        except Exception as e:
            logger.error(f"Delete failed due to {print_exception(e)}")
            raise(e)
        logger.info(f"Rows deleted : {len(delete_rows)}")
        return len(delete_rows)
    
    
    def insert_pydict(self,tablename: str, data: dict):
        '''
        insert_pydict(self,tablename: str, data: dict):
            data: { 'column_1': [value1,value2,..] , column_2: [x1,x2,..],...}
        Returns the number of rows updated.
        '''
        logging.info(f'Inserting data into {tablename} with data as a pydict')
        # Organize the data
        #Need the schema since all rows may not be inserted.
        columns = list(data.keys())
        logger.debug(f"Columns being inserted: {columns}")
        updateschema=[]
        for field in self.tableschema[tablename]:
            if field.name in columns:
                updateschema.append(field)
        logger.debug(f"Schema to update: {updateschema}")

        # create a record batch
        records = pa.RecordBatch.from_pydict(data,schema=pa.schema(updateschema))
        num_records = len(records)
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                # delete rows.
                table.insert(records)
        except Exception as e:
            logger.error(f"Insert failed due to {print_exception(e)}")
            raise(e)
        logger.info(f"Rows Inserted in ({tablename}): {num_records}")
        return num_records
    
    
    def insert_pylist(self,tablename: str, data: list):
        '''
        insert_pylist(self,tablename: str, data: dict):
        Insert rows into tablename
            data: [{'column_1': value1, 'column_2': value2 }....]
        Returns the number of rows updated.
        '''
        logging.info(f'Inserting data into {tablename} with data as a pylist of length: {len(data)}')
        # Organize the data
        # create a record batch
        records = pa.RecordBatch.from_pylist(data,schema=self.tableschema[tablename])
        num_records = len(records)
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                # delete rows.
                table.insert(records)
        except Exception as e:
            logger.error(f"Insert failed due to {print_exception(e)}")
            raise(e)
        logger.info(f"Rows Inserted in ({tablename}): {num_records}")
        return num_records
    
    def insert(self,tablename: str, data: dict,as_pydict: bool=True) -> int:
        '''
        insert(self,tablename: str, data: dict,as_pydict: bool=True) -> int:
        Insert rows into tablename
            if as_pydict=True (default)
                data: { 'column_1': [value1,value2,..] , column_2: [x1,x2,..],...}
            else
                data: [{'column_1': value1, 'column_2': value2 }....]
        Returns the number of rows updated.
        '''
        logging.info(f'Inserting data into {tablename} with input as_pydict={as_pydict}')
        if as_pydict:
            return self.insert_pydict(tablename,data)
        else:
            return self.insert_pylist(tablename,data)
        

    def update(self,tablename: str, data: dict, predicate: str) -> int:
        '''
        update(self,tablename: str, data: dict, predicate: str) -> int:
        Update rows in tablename matching the predicate with data.
            data: { 'column_1': new_value, column_2: new_value2,...}
            predicate: Ibis predicate used by vastdb
        Returns the number of rows updated.
        Note: This function is unsuitable for updating large amounts of data. Use the vastdb SDK to directly update the table using the session from this class.
        Return: int
        '''
        logging.info(f'Updating rows from {tablename} matching predicate {predicate}')
        #Get the row_ids;
        columns = list(data.keys())
        logger.info(f"Columns being updated: {columns}")
        try:
            # Optimization: Get column with the lowest memory cost so we don't need to fetch the whole row. 
            optimized_columns = [self._get_smallest_column(tablename=tablename)]
            # Get the row ids and we want to process the whole $row_id column. Need internal_rowid=True.
            pyarrow_table = self._select(tablename=tablename,column_names=optimized_columns, predicate=predicate,internal_rowid=True)
        except Exception as e:
            logger.error(f"Select row_ids failed due to {print_exception(e)}")
            raise(e)
        
        if len(pyarrow_table) == 0:
            logger.info("No rows to update.")
            return 0
        
        # Now update the rows
        # Prep the data as a pa.RecordBatch.
        # First get the schema that matches the data being updated.
        # get the field types for the columns
        updateschema=[pa.field('$row_id',pa.uint64())]
        for field in self.tableschema[tablename]:
            if field.name in columns:
                updateschema.append(field)
        logger.info(f"Schema to update: {updateschema}")

        update_data={}
        for column in columns:
            update_data[column] =[]

        for _ in range(0,len(pyarrow_table)):
            for column in columns:
                update_data[column].append(data[column])
        
        update_data['$row_id'] = pyarrow_table.to_pydict()['$row_id']
        logger.debug(update_data)

        # create a record batch
        records = pa.RecordBatch.from_pydict(update_data,schema=pa.schema(updateschema))
        logger.info(records)

        # Now update the table
        try:
            with self._session.transaction() as tx:
                table = self.get_table(tx,tablename)
                # delete rows.
                table.update(records)
        except Exception as e:
            logger.error(f"Update failed due to {print_exception(e)}")
            raise(e)
        logger.info(f"Rows Updated : {len(pyarrow_table)}")
        return len(pyarrow_table)