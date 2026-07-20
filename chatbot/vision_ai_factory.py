"""
Vision AI Factory - Supports multiple vision providers
Allows easy switching between Bedrock, Ollama, and future providers
"""

import os
from typing import Literal

VisionProvider = Literal["bedrock", "ollama", "auto"]


class VisionAIFactory:
    """
    Factory for creating Vision AI instances
    Supports multiple providers for flexibility and cost optimization
    """

    @staticmethod
    def create(
        provider: VisionProvider = "auto",
        **kwargs
    ):
        """
        Create a Vision AI instance based on provider

        Args:
            provider: Vision provider to use
                - "bedrock": AWS Bedrock Vision ($0.03/diagram)
                - "ollama": Ollama + Llama 3.2 Vision (FREE)
                - "auto": Automatically select best available provider

        Returns:
            Vision AI instance (bedrock or ollama)
        """

        # Auto-detect best provider
        if provider == "auto":
            provider = VisionAIFactory._auto_detect_provider()

        # Create provider instance
        if provider == "ollama":
            return VisionAIFactory._create_ollama(**kwargs)
        elif provider == "bedrock":
            return VisionAIFactory._create_bedrock(**kwargs)
        else:
            raise ValueError(
                f"Unknown vision provider: {provider}. "
                f"Supported: 'bedrock', 'ollama', 'auto'"
            )

    @staticmethod
    def _auto_detect_provider() -> str:
        """
        Automatically detect best available vision provider

        Priority:
        1. Ollama (if available) - FREE
        2. Bedrock (fallback) - $0.03/diagram
        """

        # Check if Ollama is available
        if VisionAIFactory._is_ollama_available():
            print("✅ Auto-detected: Using Ollama (FREE)")
            return "ollama"

        # Check if Bedrock credentials are available
        if VisionAIFactory._is_bedrock_available():
            print("⚠️  Auto-detected: Using Bedrock ($0.03/diagram)")
            print("   💡 Tip: Install Ollama for FREE vision: curl -fsSL https://ollama.com/install.sh | sh")
            return "bedrock"

        # No provider available
        raise Exception(
            "❌ No vision provider available!\n"
            "   Option 1 (FREE): Install Ollama\n"
            "     curl -fsSL https://ollama.com/install.sh | sh\n"
            "     ollama pull llama3.2-vision\n"
            "   Option 2 ($0.03/diagram): Configure AWS credentials for Bedrock\n"
        )

    @staticmethod
    def _is_ollama_available() -> bool:
        """Check if Ollama is available"""
        try:
            import requests
            ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            response = requests.get(f"{ollama_host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    @staticmethod
    def _is_bedrock_available() -> bool:
        """Check if Bedrock credentials are available"""
        try:
            import boto3
            # Try to create Bedrock client
            boto3.client('bedrock-runtime')
            return True
        except:
            return False

    @staticmethod
    def _create_ollama(**kwargs):
        """Create Ollama-based Vision AI"""
        from vision_ai_ollama import VisionAIOllama

        ollama_host = kwargs.get('ollama_host') or os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        model = kwargs.get('model') or os.getenv('OLLAMA_VISION_MODEL', 'llama3.2-vision')

        return VisionAIOllama(
            ollama_host=ollama_host,
            model=model
        )

    @staticmethod
    def _create_bedrock(**kwargs):
        """Create Bedrock-based Vision AI"""
        from vision_ai import VisionAI

        region_name = kwargs.get('region_name') or os.getenv('AWS_REGION', 'us-east-1')

        return VisionAI(region_name=region_name)

    @staticmethod
    def get_cost_comparison() -> dict:
        """Get cost comparison between providers"""
        return {
            "providers": {
                "ollama": {
                    "cost_per_diagram": 0.0,
                    "cost_per_1000": 0.0,
                    "infrastructure_cost": "~$0.08/hour (EC2 t3.large)",
                    "note": "FREE - Runs on your infrastructure"
                },
                "bedrock": {
                    "cost_per_diagram": 0.03,
                    "cost_per_1000": 30.0,
                    "infrastructure_cost": "N/A (managed service)",
                    "note": "Pay-per-use API"
                }
            },
            "savings": {
                "ollama_vs_bedrock": "100% ($0.03 → $0.00 per diagram)",
                "annual_savings_1000_diagrams_monthly": "$360/year",
                "annual_savings_10000_diagrams_monthly": "$3,600/year"
            },
            "recommendation": (
                "Use Ollama for maximum cost savings. "
                "Fall back to Bedrock only if Ollama is not available or "
                "if you need the absolute highest accuracy."
            )
        }


# Example usage
if __name__ == "__main__":
    import json

    print("🏭 Vision AI Factory - Provider Selection\n")

    # Show cost comparison
    comparison = VisionAIFactory.get_cost_comparison()
    print("💰 Cost Comparison:")
    print(json.dumps(comparison, indent=2))

    print("\n" + "=" * 70)

    # Auto-detect provider
    print("\n🔍 Auto-detecting best provider...")
    try:
        vision = VisionAIFactory.create(provider="auto")
        print(f"✅ Created: {vision.__class__.__name__}")

        # Show cost estimate
        cost = vision.estimate_cost(500)
        print(f"💵 Cost: ${cost['total_cost_usd']} per diagram")

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n" + "=" * 70)

    # Manual provider selection examples
    print("\n📝 Manual Provider Selection Examples:\n")

    print("# Use Ollama (FREE)")
    print("vision = VisionAIFactory.create(provider='ollama')")

    print("\n# Use Bedrock ($0.03/diagram)")
    print("vision = VisionAIFactory.create(provider='bedrock', region_name='us-east-1')")

    print("\n# Auto-detect (recommended)")
    print("vision = VisionAIFactory.create(provider='auto')")

    print("\n# Environment variable configuration")
    print("export VISION_PROVIDER=ollama")
    print("export OLLAMA_HOST=http://localhost:11434")
    print("vision = VisionAIFactory.create()")
