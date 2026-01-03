"""
Vision AI Layer - Bedrock Vision for service detection ONLY
No code generation - only service and relationship detection
"""

import json
import boto3
from typing import Dict, List, Tuple
from schemas.architecture_schema import VisionDetectionResult
import yaml


class VisionAI:
    """
    Vision AI using Bedrock for diagram analysis
    CRITICAL: This layer ONLY detects services and connections - NO code generation
    """

    def __init__(self, region_name: str = "us-east-1"):
        """Initialize Bedrock client"""
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
        self.model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"

        # Load service registry for detection aliases
        with open('registry/service_registry.yaml', 'r') as f:
            self.service_registry = yaml.safe_load(f)

    def analyze_diagram(self, image_data: bytes) -> VisionDetectionResult:
        """
        Analyze architecture diagram using Bedrock Vision
        Returns ONLY detected services and relationships - NO code generation

        Args:
            image_data: Image bytes (PNG/JPG)

        Returns:
            VisionDetectionResult with detected services and connections
        """

        # Optimized prompt - focused ONLY on detection, not generation
        detection_prompt = self._create_detection_prompt()

        # Call Bedrock Vision API with minimal tokens to reduce cost
        response = self._invoke_vision_model(image_data, detection_prompt)

        # Parse the response into structured detection result
        detection_result = self._parse_detection_response(response)

        return detection_result

    def _create_detection_prompt(self) -> str:
        """
        Create detection-only prompt
        This prompt is optimized to extract ONLY what's needed for intent normalization
        """

        # List of known AWS services from registry
        known_services = list(self.service_registry['services'].keys())
        service_aliases = self.service_registry['service_aliases']

        prompt = f"""You are analyzing an AWS architecture diagram. Your ONLY job is to detect and list services and connections.

DO NOT generate any code, recommendations, or detailed explanations.
DO NOT suggest improvements or alternatives.

OUTPUT ONLY a JSON object with this exact structure:

{{
  "detected_services": [
    {{
      "service_type": "ec2|s3|rds|vpc|lambda|dynamodb|etc",
      "label": "name or label found in diagram",
      "hints": ["any text hints nearby like 'prod', 'private', 'HA', etc"],
      "position": "approximate location (e.g., 'left', 'center-top')"
    }}
  ],
  "detected_connections": [
    {{
      "from_service": "service identifier or label",
      "to_service": "service identifier or label",
      "connection_type": "arrow|line|bidirectional",
      "labels": ["any labels on the connection line"]
    }}
  ],
  "textual_hints": ["any important text found in the diagram"],
  "overall_pattern": "brief one-sentence description of the architecture pattern"
}}

KNOWN AWS SERVICES (use these exact names):
{', '.join(known_services)}

SERVICE DETECTION ALIASES:
{json.dumps(service_aliases, indent=2)}

IMPORTANT:
- If you see "EC2", "Virtual Machine", "Server" -> use "ec2"
- If you see "S3", "Storage", "Bucket" -> use "s3"
- If you see "RDS", "Database", "PostgreSQL", "MySQL" -> use "rds"
- If you see "Lambda", "Function" -> use "lambda"
- If you see "VPC", "Network" -> use "vpc"
- If you see "ALB", "Load Balancer", "ELB" -> use "alb"
- Use the service_type from the KNOWN AWS SERVICES list above

Extract ONLY what you see - do not infer or add services not present in the diagram.
Return ONLY the JSON - no markdown, no explanations.
"""

        return prompt

    def _invoke_vision_model(self, image_data: bytes, prompt: str) -> str:
        """
        Invoke Bedrock Vision model with cost optimization
        """

        # Prepare request body
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,  # Reduced from default to save cost
            "temperature": 0,    # Deterministic output
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data.decode('utf-8') if isinstance(image_data, bytes) else image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        try:
            # Invoke model
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json"
            )

            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']

        except Exception as e:
            raise Exception(f"Vision AI invocation failed: {str(e)}")

    def _parse_detection_response(self, response_text: str) -> VisionDetectionResult:
        """
        Parse Vision AI response into structured detection result
        """

        try:
            # Extract JSON from response (handle markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith('```'):
                # Remove markdown code blocks
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])

            # Parse JSON
            detection_data = json.loads(response_text)

            # Create VisionDetectionResult
            result = VisionDetectionResult(
                detected_services=detection_data.get('detected_services', []),
                detected_connections=detection_data.get('detected_connections', []),
                textual_hints=detection_data.get('textual_hints', []),
                confidence_score=0.8,  # Default confidence
                raw_analysis=response_text
            )

            return result

        except json.JSONDecodeError as e:
            # Fallback: create empty result with raw text
            return VisionDetectionResult(
                detected_services=[],
                detected_connections=[],
                textual_hints=[],
                confidence_score=0.0,
                raw_analysis=response_text
            )

    def estimate_cost(self, image_size_kb: float) -> Dict[str, float]:
        """
        Estimate Bedrock Vision API cost
        Based on: https://aws.amazon.com/bedrock/pricing/

        Args:
            image_size_kb: Image size in KB

        Returns:
            Cost breakdown
        """

        # Claude 3.5 Sonnet pricing (as of 2024)
        # Input: $3 per 1M tokens
        # Output: $15 per 1M tokens
        # Images: Counted as ~1.5K tokens per image

        image_tokens = 1500  # Approximate tokens per image
        prompt_tokens = 500  # Detection prompt tokens
        output_tokens = 2000  # Max output tokens

        total_input_tokens = image_tokens + prompt_tokens
        total_output_tokens = output_tokens

        input_cost = (total_input_tokens / 1_000_000) * 3.0
        output_cost = (total_output_tokens / 1_000_000) * 15.0
        total_cost = input_cost + output_cost

        return {
            "input_cost_usd": round(input_cost, 4),
            "output_cost_usd": round(output_cost, 4),
            "total_cost_usd": round(total_cost, 4),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens
        }


# Example usage and testing
if __name__ == "__main__":
    import base64

    # Initialize Vision AI
    vision = VisionAI()

    # Example: Analyze a diagram
    # with open("sample_diagram.png", "rb") as f:
    #     image_data = base64.b64encode(f.read())
    #     result = vision.analyze_diagram(image_data)
    #     print(json.dumps(result.dict(), indent=2))

    # Estimate cost
    cost = vision.estimate_cost(image_size_kb=500)
    print(f"Estimated cost per diagram analysis: ${cost['total_cost_usd']}")
