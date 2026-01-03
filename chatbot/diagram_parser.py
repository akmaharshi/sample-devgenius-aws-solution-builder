"""
Diagram Parser for DevGenius
Supports multiple diagram formats: PNG, JPEG, draw.io, Lucid Charts, etc.
Extracts infrastructure components using AI vision and parsing
"""
import os
import json
import base64
import xml.etree.ElementTree as ET
from io import BytesIO
from PIL import Image
import boto3
from botocore.config import Config
from typing import Dict, List, Any, Optional, Tuple


class DiagramParser:
    """Parse architecture diagrams in various formats"""

    SUPPORTED_FORMATS = {
        'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
        'drawio': ['.drawio', '.xml'],
        'lucid': ['.lucid', '.lucidchart'],
        'visio': ['.vsdx', '.vsd']
    }

    def __init__(self, bedrock_client=None):
        """
        Initialize diagram parser

        Args:
            bedrock_client: Boto3 Bedrock client for AI analysis
        """
        self.bedrock_client = bedrock_client
        if not self.bedrock_client:
            aws_region = os.getenv("AWS_REGION", "us-west-2")
            config = Config(read_timeout=1000, retries=dict(max_attempts=5))
            try:
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=aws_region,
                    config=config
                )
            except Exception as e:
                print(f"Warning: Could not initialize Bedrock client: {e}")
                self.bedrock_client = None

    def detect_format(self, file_path: str, file_content: bytes = None) -> str:
        """
        Detect diagram format

        Args:
            file_path: Path to the file
            file_content: File content bytes

        Returns:
            Format type: 'image', 'drawio', 'lucid', 'visio', or 'unknown'
        """
        ext = os.path.splitext(file_path.lower())[1]

        for format_type, extensions in self.SUPPORTED_FORMATS.items():
            if ext in extensions:
                return format_type

        # Check content if extension unknown
        if file_content:
            if file_content.startswith(b'<?xml') or file_content.startswith(b'<mxfile'):
                return 'drawio'
            elif file_content.startswith(b'PK'):  # ZIP format (Lucid/Visio)
                return 'lucid'

        return 'unknown'

    def parse_diagram(
        self,
        file_path: str,
        file_content: bytes
    ) -> Dict[str, Any]:
        """
        Parse diagram and extract infrastructure components

        Args:
            file_path: Path to the diagram file
            file_content: File content bytes

        Returns:
            Dictionary with parsed components and metadata
        """
        format_type = self.detect_format(file_path, file_content)

        if format_type == 'image':
            return self.parse_image_diagram(file_content)
        elif format_type == 'drawio':
            return self.parse_drawio_diagram(file_content)
        elif format_type == 'lucid':
            return self.parse_lucid_diagram(file_content)
        else:
            return {
                'success': False,
                'error': f'Unsupported format: {format_type}',
                'components': []
            }

    def parse_image_diagram(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Parse image-based diagram using AI vision

        Args:
            image_bytes: Image file bytes

        Returns:
            Parsed infrastructure components
        """
        if not self.bedrock_client:
            return {
                'success': False,
                'error': 'Bedrock client not available',
                'components': []
            }

        # Resize image if too large
        image = Image.open(BytesIO(image_bytes))
        max_size = (1024, 1024)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            image_bytes = buffer.getvalue()

        # Prepare prompt for AI analysis
        analysis_prompt = """
        Analyze this AWS architecture diagram and extract the following information in JSON format:

        1. List all AWS services/components visible in the diagram
        2. Identify the relationships and connections between components
        3. Determine the data flow and network architecture
        4. Extract any labels, names, or identifiers for resources
        5. Identify security groups, VPCs, subnets if visible
        6. Note any specific configurations or settings mentioned

        Provide the output in this JSON structure:
        {
            "services": [
                {
                    "type": "EC2|S3|RDS|Lambda|VPC|etc",
                    "name": "resource-name",
                    "properties": {},
                    "connections": ["connected-to-service-name"]
                }
            ],
            "network": {
                "vpc": "vpc-details",
                "subnets": [],
                "security_groups": []
            },
            "data_flow": "description of data flow",
            "notes": "any additional observations"
        }
        """

        try:
            # Call Bedrock with vision capability
            response = self.bedrock_client.invoke_model(
                modelId=os.getenv(
                    "BEDROCK_MODEL_ID",
                    "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
                ),
                contentType='application/json',
                accept='application/json',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64.b64encode(image_bytes).decode('utf-8')
                                }
                            },
                            {
                                "type": "text",
                                "text": analysis_prompt
                            }
                        ]
                    }]
                })
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            ai_response = response_body['content'][0]['text']

            # Extract JSON from response
            components = self._extract_json_from_text(ai_response)

            return {
                'success': True,
                'format': 'image',
                'components': components.get('services', []),
                'network': components.get('network', {}),
                'data_flow': components.get('data_flow', ''),
                'notes': components.get('notes', ''),
                'raw_analysis': ai_response
            }

        except Exception as e:
            print(f"Error parsing image diagram: {e}")
            return {
                'success': False,
                'error': str(e),
                'components': []
            }

    def parse_drawio_diagram(self, xml_bytes: bytes) -> Dict[str, Any]:
        """
        Parse draw.io XML diagram

        Args:
            xml_bytes: draw.io XML file bytes

        Returns:
            Parsed infrastructure components
        """
        try:
            # Parse XML
            root = ET.fromstring(xml_bytes.decode('utf-8'))

            components = []
            connections = []

            # Find all cells in the diagram
            for cell in root.iter('mxCell'):
                cell_value = cell.get('value', '')
                cell_style = cell.get('style', '')
                cell_id = cell.get('id', '')
                source = cell.get('source')
                target = cell.get('target')

                # Check if it's a service/component
                if cell_value and not source and not target:
                    # Try to identify AWS service type
                    service_type = self._identify_service_from_drawio(
                        cell_value,
                        cell_style
                    )

                    components.append({
                        'id': cell_id,
                        'type': service_type,
                        'name': cell_value,
                        'properties': {},
                        'connections': []
                    })

                # Check if it's a connection
                elif source and target:
                    connections.append({
                        'source': source,
                        'target': target,
                        'label': cell_value
                    })

            # Map connections to components
            component_map = {c['id']: c for c in components}
            for conn in connections:
                if conn['source'] in component_map:
                    component_map[conn['source']]['connections'].append(
                        conn['target']
                    )

            return {
                'success': True,
                'format': 'drawio',
                'components': components,
                'connections': connections,
                'network': {},
                'notes': f'Parsed {len(components)} components from draw.io diagram'
            }

        except Exception as e:
            print(f"Error parsing draw.io diagram: {e}")
            return {
                'success': False,
                'error': str(e),
                'components': []
            }

    def parse_lucid_diagram(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        Parse Lucid Chart diagram

        Args:
            file_bytes: Lucid chart file bytes

        Returns:
            Parsed infrastructure components
        """
        # Lucid charts are in a proprietary format
        # For now, return placeholder for future implementation
        return {
            'success': False,
            'error': 'Lucid Chart parsing not yet implemented. Please export as PNG or draw.io format.',
            'components': [],
            'notes': 'Please convert Lucid Chart to PNG, JPEG, or draw.io format for parsing.'
        }

    def _identify_service_from_drawio(
        self,
        value: str,
        style: str
    ) -> str:
        """
        Identify AWS service type from draw.io cell

        Args:
            value: Cell value/label
            style: Cell style string

        Returns:
            Service type identifier
        """
        value_lower = value.lower()
        style_lower = style.lower()

        # Common AWS service keywords
        service_map = {
            'ec2': 'EC2',
            'instance': 'EC2',
            's3': 'S3',
            'bucket': 'S3',
            'rds': 'RDS',
            'database': 'RDS',
            'lambda': 'Lambda',
            'function': 'Lambda',
            'vpc': 'VPC',
            'subnet': 'Subnet',
            'elb': 'LoadBalancer',
            'alb': 'ALB',
            'nlb': 'NLB',
            'cloudfront': 'CloudFront',
            'route53': 'Route53',
            'iam': 'IAM',
            'security group': 'SecurityGroup',
            'dynamodb': 'DynamoDB',
            'sqs': 'SQS',
            'sns': 'SNS',
            'api gateway': 'APIGateway',
            'ecs': 'ECS',
            'eks': 'EKS',
            'fargate': 'Fargate'
        }

        # Check value and style for service keywords
        for keyword, service_type in service_map.items():
            if keyword in value_lower or keyword in style_lower:
                return service_type

        return 'Unknown'

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON object from AI response text

        Args:
            text: Text containing JSON

        Returns:
            Parsed JSON dictionary
        """
        try:
            # Try to find JSON in code blocks
            if '```json' in text:
                json_start = text.find('```json') + 7
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '```' in text:
                json_start = text.find('```') + 3
                json_end = text.find('```', json_start)
                json_text = text[json_start:json_end].strip()
            elif '{' in text and '}' in text:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                json_text = text[json_start:json_end]
            else:
                json_text = text

            return json.loads(json_text)
        except Exception as e:
            print(f"Error extracting JSON: {e}")
            return {
                'services': [],
                'network': {},
                'data_flow': '',
                'notes': 'Could not parse AI response as JSON'
            }

    def generate_terraform_structure(
        self,
        parsed_diagram: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate modular Terraform structure from parsed diagram

        Args:
            parsed_diagram: Parsed diagram data

        Returns:
            Dictionary of Terraform files (filename -> content)
        """
        if not parsed_diagram.get('success'):
            return {}

        components = parsed_diagram.get('components', [])
        network = parsed_diagram.get('network', {})

        terraform_files = {}

        # Group components by type
        component_groups = {}
        for component in components:
            comp_type = component.get('type', 'Unknown')
            if comp_type not in component_groups:
                component_groups[comp_type] = []
            component_groups[comp_type].append(component)

        # Generate main.tf
        terraform_files['main.tf'] = self._generate_main_tf(component_groups)

        # Generate variables.tf
        terraform_files['variables.tf'] = self._generate_variables_tf()

        # Generate outputs.tf
        terraform_files['outputs.tf'] = self._generate_outputs_tf(component_groups)

        # Generate modules for each service type
        for service_type, components_list in component_groups.items():
            if service_type != 'Unknown':
                module_files = self._generate_module_files(
                    service_type,
                    components_list
                )
                for filename, content in module_files.items():
                    terraform_files[f'modules/{service_type.lower()}/{filename}'] = content

        return terraform_files

    def _generate_main_tf(self, component_groups: Dict[str, List]) -> str:
        """Generate main.tf file"""
        content = """# Generated by DevGenius
# Main Terraform configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.common_tags
  }
}

"""

        # Add module calls for each service type
        for service_type in component_groups.keys():
            if service_type != 'Unknown':
                content += f"""
module "{service_type.lower()}" {{
  source = "./modules/{service_type.lower()}"

  environment = var.environment
  project_name = var.project_name
}}

"""

        return content

    def _generate_variables_tf(self) -> str:
        """Generate variables.tf file"""
        return """# Generated by DevGenius
# Terraform variables

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
"""

    def _generate_outputs_tf(self, component_groups: Dict[str, List]) -> str:
        """Generate outputs.tf file"""
        content = """# Generated by DevGenius
# Terraform outputs

"""
        for service_type in component_groups.keys():
            if service_type != 'Unknown':
                content += f"""
output "{service_type.lower()}_outputs" {{
  description = "{service_type} module outputs"
  value       = module.{service_type.lower()}
}}
"""
        return content

    def _generate_module_files(
        self,
        service_type: str,
        components: List[Dict]
    ) -> Dict[str, str]:
        """Generate module files for a service type"""
        files = {}

        # Generate module main.tf
        files['main.tf'] = f"""# {service_type} Module
# Generated by DevGenius

resource "aws_{service_type.lower()}_instance" "this" {{
  count = length(var.{service_type.lower()}_configs)

  # Configuration from diagram
  # Customize based on your requirements

  tags = merge(
    var.common_tags,
    {{
      Name = "${{var.project_name}}-${{var.environment}}-{service_type.lower()}-${{count.index}}"
    }}
  )
}}
"""

        # Generate module variables.tf
        files['variables.tf'] = f"""# {service_type} Module Variables

variable "environment" {{
  description = "Environment name"
  type        = string
}}

variable "project_name" {{
  description = "Project name"
  type        = string
}}

variable "{service_type.lower()}_configs" {{
  description = "{service_type} configurations"
  type        = list(map(string))
  default     = []
}}

variable "common_tags" {{
  description = "Common tags"
  type        = map(string)
  default     = {{}}
}}
"""

        # Generate module outputs.tf
        files['outputs.tf'] = f"""# {service_type} Module Outputs

output "{service_type.lower()}_ids" {{
  description = "IDs of {service_type} resources"
  value       = aws_{service_type.lower()}_instance.this[*].id
}}
"""

        return files
