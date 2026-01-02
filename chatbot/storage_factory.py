"""
Storage factory for DevGenius
Creates appropriate storage and database clients based on configuration
"""
import os
import boto3
from botocore.config import Config
from config_manager import config
from local_storage import LocalStorageAdapter, LocalDatabaseAdapter


class StorageFactory:
    """Factory for creating storage clients"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize storage factory"""
        if not self._initialized:
            self._setup_clients()
            StorageFactory._initialized = True

    def _setup_clients(self):
        """Setup storage and database clients based on configuration"""
        if config.is_local_mode():
            self._setup_local_clients()
        else:
            self._setup_aws_clients()

    def _setup_local_clients(self):
        """Setup local storage clients"""
        local_data_path = config.get("local_data_path", "./local_data")

        # Create local storage adapter
        self.storage_adapter = LocalStorageAdapter(local_data_path)

        # Create local database adapter
        self.db_adapter = LocalDatabaseAdapter(local_data_path)

        # Storage client interface (S3-compatible)
        self.s3_client = LocalS3Client(self.storage_adapter)
        self.s3_resource = LocalS3Resource(self.storage_adapter)

        # Database client interface (DynamoDB-compatible)
        self.dynamodb_resource = LocalDynamoDBResource(self.db_adapter)

        # Set Bedrock clients (still use AWS if credentials available)
        if self._has_aws_credentials():
            aws_region = config.get("aws_region", "us-west-2")
            boto_config = Config(read_timeout=1000, retries=dict(max_attempts=5))
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region, config=boto_config)
            self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=aws_region)
        else:
            self.bedrock_client = None
            self.bedrock_agent_runtime_client = None

        # Optional AWS services
        self.secrets_client = None
        self.sts_client = None

    def _setup_aws_clients(self):
        """Setup AWS storage clients"""
        aws_region = os.getenv("AWS_REGION")
        boto_config = Config(read_timeout=1000, retries=dict(max_attempts=5))

        # AWS clients
        self.s3_client = boto3.client('s3', region_name=aws_region, config=boto_config)
        self.s3_resource = boto3.resource('s3', region_name=aws_region)
        self.dynamodb_resource = boto3.resource('dynamodb', region_name=aws_region)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region, config=boto_config)
        self.bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime', region_name=aws_region)
        self.secrets_client = boto3.client('secretsmanager', region_name=aws_region, config=boto_config)
        self.sts_client = boto3.client('sts', region_name=aws_region)

    def _has_aws_credentials(self):
        """Check if AWS credentials are available"""
        return (os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or
                os.path.exists(os.path.expanduser("~/.aws/credentials")))


class LocalS3Client:
    """Local S3-compatible client"""

    def __init__(self, storage_adapter):
        self.storage = storage_adapter

    def put_object(self, Body, Bucket, Key):
        return self.storage.put_object(Body, Bucket, Key)

    def get_object(self, Bucket, Key):
        return self.storage.get_object(Bucket, Key)

    def upload_file(self, Filename, Bucket, Key):
        with open(Filename, 'rb') as f:
            content = f.read()
        return self.storage.put_object(content, Bucket, Key)


class LocalS3Resource:
    """Local S3 resource interface"""

    def __init__(self, storage_adapter):
        self.storage = storage_adapter

    def Bucket(self, name):
        return LocalBucket(self.storage, name)


class LocalBucket:
    """Local S3 bucket interface"""

    def __init__(self, storage_adapter, bucket_name):
        self.storage = storage_adapter
        self.name = bucket_name

    def objects(self):
        return self

    def filter(self, Prefix=''):
        objects = self.storage.list_objects(self.name, Prefix)
        return [LocalObject(self.storage, self.name, obj['Key']) for obj in objects]

    def download_file(self, key, local_path):
        self.storage.download_file(self.name, key, local_path)


class LocalObject:
    """Local S3 object interface"""

    def __init__(self, storage_adapter, bucket_name, key):
        self.storage = storage_adapter
        self.bucket_name = bucket_name
        self.key = key


class LocalDynamoDBResource:
    """Local DynamoDB resource interface"""

    def __init__(self, db_adapter):
        self.db = db_adapter

    def Table(self, table_name):
        return self.db.get_table(table_name)


# Global storage factory instance
storage_factory = StorageFactory()
