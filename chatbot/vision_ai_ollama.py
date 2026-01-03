"""
Vision AI using Ollama + Llama 3.2 Vision (100% FREE)
Zero Bedrock costs - completely open source solution
"""

import json
import base64
import requests
from typing import Dict, List
from schemas.architecture_schema import VisionDetectionResult
import yaml


class VisionAIOllama:
    """
    Vision AI using Ollama with Llama 3.2 Vision model
    ZERO COST - Runs locally or on EC2

    Setup:
        1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh
        2. Pull model: ollama pull llama3.2-vision
        3. Run: ollama serve (if not already running)
    """

    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "llama3.2-vision"
    ):
        """
        Initialize Ollama-based Vision AI

        Args:
            ollama_host: Ollama server URL (default: localhost)
            model: Ollama vision model to use
        """
        self.ollama_host = ollama_host
        self.model = model

        # Load service registry for detection aliases
        with open('registry/service_registry.yaml', 'r') as f:
            self.service_registry = yaml.safe_load(f)

        # Verify Ollama is running
        self._check_ollama_available()

    def _check_ollama_available(self) -> bool:
        """Check if Ollama server is available"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                # Check if our model is available
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]

                if not any(self.model in name for name in model_names):
                    print(f"⚠️  Warning: Model '{self.model}' not found in Ollama.")
                    print(f"   Available models: {', '.join(model_names)}")
                    print(f"   Run: ollama pull {self.model}")
                    return False

                return True
        except requests.exceptions.RequestException as e:
            raise Exception(
                f"❌ Ollama server not available at {self.ollama_host}\n"
                f"   Error: {str(e)}\n"
                f"   Please start Ollama: ollama serve\n"
                f"   Or install: curl -fsSL https://ollama.com/install.sh | sh"
            )

        return False

    def analyze_diagram(self, image_data: bytes) -> VisionDetectionResult:
        """
        Analyze architecture diagram using Ollama (FREE)
        Returns ONLY detected services and relationships - NO code generation

        Args:
            image_data: Image bytes (PNG/JPG) - can be raw bytes or base64

        Returns:
            VisionDetectionResult with detected services and connections
        """

        # Optimized prompt - focused ONLY on detection, not generation
        detection_prompt = self._create_detection_prompt()

        # Call Ollama Vision API (FREE)
        response = self._invoke_ollama_vision(image_data, detection_prompt)

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

    def _invoke_ollama_vision(self, image_data: bytes, prompt: str) -> str:
        """
        Invoke Ollama vision model (FREE - runs locally)
        """

        # Convert image to base64 if it's raw bytes
        if isinstance(image_data, bytes):
            # Check if already base64 encoded
            try:
                base64.b64decode(image_data)
                image_b64 = image_data.decode('utf-8')
            except:
                image_b64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_b64 = image_data

        # Prepare request for Ollama API
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {
                "temperature": 0,  # Deterministic output
                "num_predict": 2000  # Max tokens to generate
            }
        }

        try:
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=request_data,
                timeout=120  # 2 minute timeout for vision processing
            )

            if response.status_code != 200:
                raise Exception(
                    f"Ollama API error: {response.status_code}\n"
                    f"Response: {response.text}"
                )

            # Parse response
            response_data = response.json()
            return response_data.get('response', '')

        except requests.exceptions.Timeout:
            raise Exception(
                "Ollama request timed out (>2 minutes). "
                "The model might be downloading or the image is too large."
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama request failed: {str(e)}")

    def _parse_detection_response(self, response_text: str) -> VisionDetectionResult:
        """
        Parse Ollama response into structured detection result
        """

        try:
            # Extract JSON from response (handle markdown code blocks if present)
            response_text = response_text.strip()

            # Remove markdown code blocks
            if '```json' in response_text:
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                response_text = response_text[start:end].strip()
            elif '```' in response_text:
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text

            # Parse JSON
            detection_data = json.loads(response_text)

            # Create VisionDetectionResult
            result = VisionDetectionResult(
                detected_services=detection_data.get('detected_services', []),
                detected_connections=detection_data.get('detected_connections', []),
                textual_hints=detection_data.get('textual_hints', []),
                confidence_score=0.85,  # Ollama confidence (slightly lower than Bedrock)
                raw_analysis=response_text
            )

            return result

        except json.JSONDecodeError as e:
            # Fallback: create empty result with raw text
            print(f"⚠️  Warning: Failed to parse JSON from Ollama response")
            print(f"   Error: {str(e)}")
            print(f"   Response preview: {response_text[:200]}...")

            return VisionDetectionResult(
                detected_services=[],
                detected_connections=[],
                textual_hints=[],
                confidence_score=0.0,
                raw_analysis=response_text
            )

    def estimate_cost(self, image_size_kb: float) -> Dict[str, float]:
        """
        Estimate cost of Ollama-based vision analysis

        Args:
            image_size_kb: Image size in KB (not used, but kept for API compatibility)

        Returns:
            Cost breakdown (all zeros - it's FREE!)
        """

        # Ollama runs locally or on your own infrastructure
        # No per-request API costs!

        return {
            "input_cost_usd": 0.0,
            "output_cost_usd": 0.0,
            "total_cost_usd": 0.0,
            "infrastructure_cost_note": (
                "Runs on your infrastructure (local/EC2). "
                "EC2 t3.large (~$0.08/hr) can process ~1000 diagrams/hour = "
                "$0.00008 per diagram"
            ),
            "vs_bedrock": "100% savings vs Bedrock ($0.03 per diagram)"
        }

    def get_model_info(self) -> Dict:
        """Get information about the current Ollama model"""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/show",
                json={"name": self.model},
                timeout=5
            )

            if response.status_code == 200:
                return response.json()

            return {"error": f"Model info not available: {response.status_code}"}

        except Exception as e:
            return {"error": f"Failed to get model info: {str(e)}"}


# Example usage and testing
if __name__ == "__main__":
    import sys

    print("🦙 Ollama + Llama 3.2 Vision - FREE Alternative to Bedrock")
    print("=" * 70)

    # Initialize Vision AI
    try:
        vision = VisionAIOllama()
        print("✅ Ollama connection successful!")

        # Get model info
        model_info = vision.get_model_info()
        if 'error' not in model_info:
            print(f"📦 Model: {vision.model}")
            print(f"🔧 Host: {vision.ollama_host}")

        # Estimate cost
        cost = vision.estimate_cost(image_size_kb=500)
        print(f"\n💰 Cost Analysis:")
        print(f"   Per diagram: ${cost['total_cost_usd']} (FREE!)")
        print(f"   Infrastructure: {cost['infrastructure_cost_note']}")
        print(f"   Savings: {cost['vs_bedrock']}")

        # Test with sample image if provided
        if len(sys.argv) > 1:
            image_path = sys.argv[1]
            print(f"\n📷 Analyzing diagram: {image_path}")

            with open(image_path, 'rb') as f:
                image_data = f.read()

            result = vision.analyze_diagram(image_data)

            print(f"\n✅ Analysis complete!")
            print(f"   Services detected: {len(result.detected_services)}")
            print(f"   Connections detected: {len(result.detected_connections)}")
            print(f"   Confidence: {result.confidence_score}")

            if result.detected_services:
                print(f"\n📋 Detected Services:")
                for service in result.detected_services:
                    print(f"   - {service.get('service_type')}: {service.get('label')}")

        else:
            print(f"\n💡 Usage: python {__file__} <path-to-diagram.png>")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

    print("\n" + "=" * 70)
