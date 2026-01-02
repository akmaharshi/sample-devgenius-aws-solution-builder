"""
Configuration manager for DevGenius
Handles switching between AWS and local modes
"""
import os
import json


class ConfigManager:
    """Manages configuration for AWS vs Local mode"""

    def __init__(self):
        """Initialize configuration manager"""
        # Check if running in local mode
        self.local_mode = os.getenv("LOCAL_MODE", "false").lower() == "true"

        # Load configuration
        if self.local_mode:
            self._load_local_config()
        else:
            self._load_aws_config()

    def _load_local_config(self):
        """Load configuration for local mode"""
        self.config = {
            "mode": "local",
            "s3_bucket_name": "local-bucket",
            "conversation_table_name": "conversations",
            "feedback_table_name": "feedback",
            "session_table_name": "sessions",
            "local_data_path": os.getenv("LOCAL_DATA_PATH", "./local_data"),
            "bedrock_model_id": os.getenv(
                "BEDROCK_MODEL_ID",
                "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            ),
            "aws_region": os.getenv("AWS_REGION", "us-west-2"),
            "enable_auth": os.getenv("ENABLE_AUTH", "false").lower() == "true"
        }

    def _load_aws_config(self):
        """Load configuration for AWS mode"""
        self.config = {
            "mode": "aws",
            "aws_region": os.getenv("AWS_REGION"),
            "enable_auth": True
        }

        # Load resource names from SSM parameter (if available)
        if os.getenv("AWS_RESOURCE_NAMES_PARAMETER"):
            ssm_parameter = json.loads(os.getenv("AWS_RESOURCE_NAMES_PARAMETER"))
            self.config.update(ssm_parameter)

    def is_local_mode(self):
        """Check if running in local mode"""
        return self.local_mode

    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    def get_required(self, key):
        """Get required configuration value (raises error if not found)"""
        if key not in self.config:
            raise ValueError(f"Required configuration key not found: {key}")
        return self.config[key]


# Global configuration instance
config = ConfigManager()
