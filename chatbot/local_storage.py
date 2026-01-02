"""
Local storage adapter for DevGenius
Provides local file system storage as an alternative to AWS S3
"""
import os
import json
import datetime
import shutil
import glob
from pathlib import Path


class LocalStorageAdapter:
    """Adapter for local file system storage"""

    def __init__(self, base_path="./local_data"):
        """
        Initialize local storage adapter

        Args:
            base_path: Base directory for local storage
        """
        self.base_path = base_path
        self.storage_path = os.path.join(base_path, "storage")
        self.conversations_path = os.path.join(base_path, "conversations")
        self.sessions_path = os.path.join(base_path, "sessions")
        self.feedback_path = os.path.join(base_path, "feedback")

        # Create directories if they don't exist
        for path in [self.storage_path, self.conversations_path,
                     self.sessions_path, self.feedback_path]:
            Path(path).mkdir(parents=True, exist_ok=True)

    def put_object(self, body, bucket, key):
        """
        Store content locally (S3-compatible interface)

        Args:
            body: Content to store
            bucket: Bucket name (used as subdirectory)
            key: Object key (file path)
        """
        file_path = os.path.join(self.storage_path, bucket, key)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if isinstance(body, str):
            with open(file_path, 'w') as f:
                f.write(body)
        else:
            with open(file_path, 'wb') as f:
                f.write(body)

        return {'ETag': 'local-storage'}

    def get_object(self, bucket, key):
        """
        Retrieve content from local storage

        Args:
            bucket: Bucket name
            key: Object key
        """
        file_path = os.path.join(self.storage_path, bucket, key)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Object not found: {key}")

        with open(file_path, 'rb') as f:
            content = f.read()

        return {'Body': content}

    def list_objects(self, bucket, prefix=''):
        """
        List objects in local storage

        Args:
            bucket: Bucket name
            prefix: Object prefix filter
        """
        search_path = os.path.join(self.storage_path, bucket, prefix, '**', '*')
        files = glob.glob(search_path, recursive=True)

        objects = []
        for file_path in files:
            if os.path.isfile(file_path):
                relative_key = os.path.relpath(
                    file_path,
                    os.path.join(self.storage_path, bucket)
                )
                objects.append({
                    'Key': relative_key,
                    'Size': os.path.getsize(file_path)
                })

        return objects

    def download_file(self, bucket, key, local_path):
        """
        Download file from storage to local path

        Args:
            bucket: Bucket name
            key: Object key
            local_path: Destination path
        """
        source_path = os.path.join(self.storage_path, bucket, key)
        shutil.copy2(source_path, local_path)


class LocalDatabaseAdapter:
    """Adapter for local JSON-based database (DynamoDB alternative)"""

    def __init__(self, base_path="./local_data"):
        """
        Initialize local database adapter

        Args:
            base_path: Base directory for local data
        """
        self.base_path = base_path
        self.tables = {}

        # Create base path
        Path(base_path).mkdir(parents=True, exist_ok=True)

    def get_table(self, table_name):
        """Get or create a table"""
        if table_name not in self.tables:
            table_path = os.path.join(self.base_path, f"{table_name}.json")
            self.tables[table_name] = LocalTable(table_path)
        return self.tables[table_name]


class LocalTable:
    """Local JSON-based table (DynamoDB-compatible interface)"""

    def __init__(self, file_path):
        """
        Initialize local table

        Args:
            file_path: Path to JSON file for storing data
        """
        self.file_path = file_path
        self._load_data()

    def _load_data(self):
        """Load data from JSON file"""
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = []

    def _save_data(self):
        """Save data to JSON file"""
        with open(self.file_path, 'w') as f:
            json.dump(self.data, f, indent=2)

    def put_item(self, Item):
        """
        Add item to table

        Args:
            Item: Item dictionary to store
        """
        # Add timestamp if not present
        if 'created_at' not in Item:
            Item['created_at'] = datetime.datetime.now(
                tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")

        # Append item
        self.data.append(Item)
        self._save_data()

        return {'ResponseMetadata': {'HTTPStatusCode': 200}}

    def get_item(self, Key):
        """
        Get item from table

        Args:
            Key: Dictionary with key attributes
        """
        for item in self.data:
            if all(item.get(k) == v for k, v in Key.items()):
                return {'Item': item}

        return {}

    def query(self, KeyConditionExpression=None, **kwargs):
        """
        Query items (simplified implementation)

        Args:
            KeyConditionExpression: Query expression (not fully implemented)
        """
        # Simple implementation - return all items
        return {'Items': self.data}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues, **kwargs):
        """
        Update item in table

        Args:
            Key: Dictionary with key attributes
            UpdateExpression: Update expression string
            ExpressionAttributeValues: Values for expression
        """
        for item in self.data:
            if all(item.get(k) == v for k, v in Key.items()):
                # Parse simple SET expressions
                if UpdateExpression.startswith('SET '):
                    updates = UpdateExpression[4:].split(',')
                    for update in updates:
                        attr_name, value_ref = update.strip().split(' = ')
                        attr_name = attr_name.strip()
                        value_ref = value_ref.strip()

                        if value_ref in ExpressionAttributeValues:
                            item[attr_name] = ExpressionAttributeValues[value_ref]

                self._save_data()
                return {'Attributes': item}

        return {}
