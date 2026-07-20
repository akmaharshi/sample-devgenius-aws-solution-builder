"""
IaC Orchestrator - Main workflow coordinator
Orchestrates the complete diagram-to-terraform pipeline with minimal Bedrock usage
"""

import os
import json
import base64
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from vision_ai_factory import VisionAIFactory
from intent_normalizer import IntentNormalizer
from terraform_generator import TerraformGenerator
from terraform_validator import TerraformValidator, ValidationResult, SecurityScanResult
from schemas.architecture_schema import ArchitectureIntent, VisionDetectionResult


class IaCOrchestrator:
    """
    Main orchestrator for the AI-IaC platform
    Coordinates: Vision AI → Intent Normalization → Terraform Generation → Validation

    COST OPTIMIZATION:
    - Vision AI: Ollama (FREE) or Bedrock ($0.03) - auto-detects best option
    - All code generation uses templates (ZERO Bedrock cost)
    - Deterministic outputs (same input → same Terraform)
    """

    def __init__(
        self,
        aws_region: str = "us-east-1",
        output_base_dir: str = "generated_architectures",
        vision_provider: str = "auto"
    ):
        """
        Initialize orchestrator with all components

        Args:
            aws_region: AWS region for infrastructure
            output_base_dir: Base directory for generated Terraform
            vision_provider: Vision AI provider ('auto', 'ollama', 'bedrock')
                - 'auto': Auto-detect best available (Ollama → Bedrock)
                - 'ollama': Use Ollama (FREE)
                - 'bedrock': Use AWS Bedrock ($0.03/diagram)
        """

        self.aws_region = aws_region
        self.output_base_dir = output_base_dir
        self.vision_provider = vision_provider

        # Initialize components
        self.vision_ai = VisionAIFactory.create(
            provider=vision_provider,
            region_name=aws_region
        )
        self.intent_normalizer = IntentNormalizer()
        self.terraform_generator = TerraformGenerator()

        # Create output directory
        Path(output_base_dir).mkdir(parents=True, exist_ok=True)

    def process_diagram(
        self,
        image_path: str,
        architecture_name: str,
        user_clarifications: Optional[Dict] = None,
        validate_terraform: bool = True,
        run_security_scan: bool = True
    ) -> Dict:
        """
        Complete workflow: Diagram → Terraform

        Args:
            image_path: Path to architecture diagram image
            architecture_name: Name for the architecture
            user_clarifications: User-provided clarifications
            validate_terraform: Whether to run terraform validate
            run_security_scan: Whether to run security scanning

        Returns:
            Dictionary with results, including:
            - vision_result: Vision AI detection
            - architecture_intent: Normalized intent
            - terraform_files: Generated Terraform
            - validation_result: Validation results
            - security_result: Security scan results
            - cost_breakdown: Cost analysis
            - questions: Questions needing user input
        """

        results = {
            "success": False,
            "architecture_name": architecture_name,
            "cost_breakdown": {},
            "questions": []
        }

        try:
            # STEP 1: Vision AI - Analyze diagram (ONLY Bedrock call)
            print("📷 Step 1: Analyzing diagram with Vision AI...")
            vision_result, vision_cost = self._analyze_diagram(image_path)
            results["vision_result"] = vision_result.dict()
            results["cost_breakdown"]["vision_ai"] = vision_cost

            # STEP 2: Intent Normalization - NO Bedrock
            print("🎯 Step 2: Normalizing architecture intent...")
            architecture_intent, questions = self._normalize_intent(
                vision_result,
                user_clarifications or {},
                architecture_name
            )
            results["architecture_intent"] = architecture_intent.dict()
            results["questions"] = questions

            # If there are unanswered questions, pause and return
            if questions and not user_clarifications:
                results["status"] = "needs_clarification"
                results["message"] = "Please provide clarifications for the following questions"
                return results

            # STEP 3: Terraform Generation - NO Bedrock (template-based)
            print("🔧 Step 3: Generating Terraform code...")
            terraform_files, output_dir = self._generate_terraform(
                architecture_intent,
                architecture_name
            )
            results["terraform_files"] = list(terraform_files.keys())
            results["output_directory"] = output_dir
            results["cost_breakdown"]["terraform_generation"] = 0.0  # ZERO cost!

            # STEP 4: Validation - NO Bedrock
            if validate_terraform:
                print("✅ Step 4: Validating Terraform...")
                validation_result = self._validate_terraform(output_dir)
                results["validation_result"] = {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.error_messages,
                    "warnings": validation_result.warning_messages,
                    "info": validation_result.info_messages
                }

                if not validation_result.is_valid:
                    results["status"] = "validation_failed"
                    results["message"] = "Terraform validation failed"
                    return results

            # STEP 5: Security Scanning - NO Bedrock
            if run_security_scan:
                print("🔒 Step 5: Running security scan...")
                security_result = self._scan_security(output_dir)
                results["security_result"] = {
                    "passed": security_result.passed,
                    "failed_checks": security_result.failed_checks,
                    "passed_checks": security_result.passed_checks,
                    "severity_breakdown": security_result.severity_breakdown,
                    "critical_issues": [
                        issue for issue in security_result.issues
                        if issue.get('severity') in ['CRITICAL', 'HIGH']
                    ][:10]  # Show first 10 critical/high issues
                }

            # Calculate total cost
            total_cost = sum(
                cost for cost in results["cost_breakdown"].values()
                if isinstance(cost, (int, float))
            )
            results["cost_breakdown"]["total_usd"] = round(total_cost, 4)

            results["success"] = True
            results["status"] = "completed"
            results["message"] = f"Successfully generated Terraform for {architecture_name}"

            return results

        except Exception as e:
            results["success"] = False
            results["status"] = "error"
            results["message"] = f"Error: {str(e)}"
            return results

    def _analyze_diagram(self, image_path: str) -> Tuple[VisionDetectionResult, float]:
        """
        Step 1: Analyze diagram with Vision AI
        This is the ONLY step that uses Bedrock
        """

        # Read image
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read())

        # Get image size for cost estimation
        image_size_kb = os.path.getsize(image_path) / 1024

        # Analyze with Vision AI
        vision_result = self.vision_ai.analyze_diagram(image_data)

        # Estimate cost
        cost_breakdown = self.vision_ai.estimate_cost(image_size_kb)

        return vision_result, cost_breakdown['total_cost_usd']

    def _normalize_intent(
        self,
        vision_result: VisionDetectionResult,
        user_clarifications: Dict,
        architecture_name: str
    ) -> Tuple[ArchitectureIntent, List[str]]:
        """
        Step 2: Normalize intent
        NO Bedrock usage - pure Python logic
        """

        architecture, questions = self.intent_normalizer.normalize(
            vision_result,
            user_clarifications,
            architecture_name
        )

        return architecture, questions

    def _generate_terraform(
        self,
        architecture: ArchitectureIntent,
        architecture_name: str
    ) -> Tuple[Dict[str, str], str]:
        """
        Step 3: Generate Terraform
        NO Bedrock usage - template-based generation
        """

        output_dir = os.path.join(self.output_base_dir, architecture_name)
        terraform_files = self.terraform_generator.generate(
            architecture,
            output_dir=output_dir
        )

        return terraform_files, output_dir

    def _validate_terraform(self, terraform_dir: str) -> ValidationResult:
        """
        Step 4: Validate Terraform
        NO Bedrock usage - runs terraform validate
        """

        validator = TerraformValidator(terraform_dir)
        return validator.validate()

    def _scan_security(self, terraform_dir: str) -> SecurityScanResult:
        """
        Step 5: Security scanning
        NO Bedrock usage - runs Checkov
        """

        validator = TerraformValidator(terraform_dir)
        return validator.scan_security(framework="checkov", fail_on_severity="HIGH")

    def cost_comparison(self, num_diagrams: int = 1) -> Dict:
        """
        Compare costs: Old approach (LLM-based) vs New approaches (Template + Bedrock/Ollama)

        Args:
            num_diagrams: Number of diagrams to estimate for

        Returns:
            Cost comparison breakdown
        """

        # OLD APPROACH (Original LLM-based implementation)
        # - Vision AI: ~$0.03 per diagram
        # - Agent invocation: ~$0.05 per conversation
        # - CDK generation: ~$0.10 (128K tokens @ $15/M output)
        # - CFN generation: ~$0.10
        # - Cost estimate: ~$0.05
        # - Documentation: ~$0.05
        # - Architecture diagram: ~$0.15 (extended thinking)
        # Total per diagram: ~$0.53

        old_approach_per_diagram = 0.53
        old_approach_total = old_approach_per_diagram * num_diagrams

        # NEW APPROACH - BEDROCK VISION (Template-based)
        # - Vision AI: ~$0.03 per diagram (ONLY Bedrock usage)
        # - Intent normalization: $0 (pure Python)
        # - Terraform generation: $0 (templates)
        # - Validation: $0 (terraform CLI)
        # - Security scan: $0 (Checkov)
        # Total per diagram: ~$0.03

        new_bedrock_per_diagram = 0.03
        new_bedrock_total = new_bedrock_per_diagram * num_diagrams

        # NEW APPROACH - OLLAMA (Template-based + FREE Vision)
        # - Vision AI: ~$0.00 (Ollama - runs on your infrastructure)
        # - Intent normalization: $0 (pure Python)
        # - Terraform generation: $0 (templates)
        # - Validation: $0 (terraform CLI)
        # - Security scan: $0 (Checkov)
        # Total per diagram: ~$0.00

        new_ollama_per_diagram = 0.0
        new_ollama_total = new_ollama_per_diagram * num_diagrams

        # Savings - Bedrock
        savings_bedrock_per = old_approach_per_diagram - new_bedrock_per_diagram
        savings_bedrock_total = old_approach_total - new_bedrock_total
        savings_bedrock_pct = (savings_bedrock_per / old_approach_per_diagram) * 100

        # Savings - Ollama
        savings_ollama_per = old_approach_per_diagram - new_ollama_per_diagram
        savings_ollama_total = old_approach_total - new_ollama_total
        savings_ollama_pct = (savings_ollama_per / old_approach_per_diagram) * 100

        return {
            "old_approach": {
                "name": "LLM-based generation",
                "per_diagram_usd": round(old_approach_per_diagram, 2),
                "total_usd": round(old_approach_total, 2),
                "breakdown": {
                    "vision_ai": 0.03,
                    "agent_invocation": 0.05,
                    "cdk_generation": 0.10,
                    "cfn_generation": 0.10,
                    "cost_estimate": 0.05,
                    "documentation": 0.05,
                    "architecture_diagram": 0.15
                }
            },
            "new_approach_bedrock": {
                "name": "Template-based + Bedrock Vision",
                "per_diagram_usd": round(new_bedrock_per_diagram, 2),
                "total_usd": round(new_bedrock_total, 2),
                "breakdown": {
                    "vision_ai_bedrock": 0.03,
                    "intent_normalization": 0.0,
                    "terraform_generation": 0.0,
                    "validation": 0.0,
                    "security_scan": 0.0
                },
                "savings_vs_old": {
                    "per_diagram_usd": round(savings_bedrock_per, 2),
                    "total_usd": round(savings_bedrock_total, 2),
                    "percentage": round(savings_bedrock_pct, 1)
                }
            },
            "new_approach_ollama": {
                "name": "Template-based + Ollama (FREE)",
                "per_diagram_usd": round(new_ollama_per_diagram, 2),
                "total_usd": round(new_ollama_total, 2),
                "breakdown": {
                    "vision_ai_ollama": 0.0,
                    "intent_normalization": 0.0,
                    "terraform_generation": 0.0,
                    "validation": 0.0,
                    "security_scan": 0.0
                },
                "infrastructure_note": "Runs on your infrastructure (local/EC2 ~$0.08/hour)",
                "savings_vs_old": {
                    "per_diagram_usd": round(savings_ollama_per, 2),
                    "total_usd": round(savings_ollama_total, 2),
                    "percentage": round(savings_ollama_pct, 1)
                }
            },
            "num_diagrams": num_diagrams,
            "recommendation": (
                "Use Ollama for 100% cost savings. "
                "Fall back to Bedrock only if Ollama is unavailable or you need absolute highest accuracy."
            )
        }


# Example usage and CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI-IaC Platform - Diagram to Terraform")
    parser.add_argument("--image", help="Path to architecture diagram image")
    parser.add_argument("--name", help="Architecture name")
    parser.add_argument("--env", default="dev", choices=["dev", "staging", "prod"],
                        help="Environment (default: dev)")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--vision-provider", default="auto",
                        choices=["auto", "ollama", "bedrock"],
                        help="Vision AI provider: auto (default), ollama (FREE), bedrock ($0.03)")
    parser.add_argument("--no-validate", action="store_true", help="Skip Terraform validation")
    parser.add_argument("--no-security-scan", action="store_true", help="Skip security scanning")
    parser.add_argument("--cost-comparison", action="store_true",
                        help="Show cost comparison between old and new approaches")

    args = parser.parse_args()

    # Cost comparison
    if args.cost_comparison:
        # Create temporary orchestrator for cost comparison
        temp_orchestrator = IaCOrchestrator(aws_region=args.region, vision_provider="auto")

        print("\n💰 Cost Comparison: LLM-based vs Template-based (Bedrock vs Ollama)")
        print("=" * 80)
        comparison = temp_orchestrator.cost_comparison(num_diagrams=100)

        print(f"\n📊 OLD APPROACH ({comparison['old_approach']['name']}):")
        print(f"  Per diagram: ${comparison['old_approach']['per_diagram_usd']}")
        print(f"  100 diagrams: ${comparison['old_approach']['total_usd']}")

        print(f"\n📊 NEW APPROACH - BEDROCK ({comparison['new_approach_bedrock']['name']}):")
        print(f"  Per diagram: ${comparison['new_approach_bedrock']['per_diagram_usd']}")
        print(f"  100 diagrams: ${comparison['new_approach_bedrock']['total_usd']}")
        print(f"  💵 Savings: ${comparison['new_approach_bedrock']['savings_vs_old']['per_diagram_usd']} "
              f"({comparison['new_approach_bedrock']['savings_vs_old']['percentage']}%)")

        print(f"\n📊 NEW APPROACH - OLLAMA ({comparison['new_approach_ollama']['name']}):")
        print(f"  Per diagram: ${comparison['new_approach_ollama']['per_diagram_usd']} 🎉 FREE!")
        print(f"  100 diagrams: ${comparison['new_approach_ollama']['total_usd']}")
        print(f"  💵 Savings: ${comparison['new_approach_ollama']['savings_vs_old']['per_diagram_usd']} "
              f"({comparison['new_approach_ollama']['savings_vs_old']['percentage']}%)")
        print(f"  ℹ️  {comparison['new_approach_ollama']['infrastructure_note']}")

        print(f"\n💡 Recommendation:")
        print(f"  {comparison['recommendation']}")
        print("=" * 80)
        exit(0)

    # Validate required arguments
    if not args.image or not args.name:
        parser.error("--image and --name are required (unless using --cost-comparison)")

    # Initialize orchestrator
    orchestrator = IaCOrchestrator(
        aws_region=args.region,
        vision_provider=args.vision_provider
    )

    # Process diagram
    user_clarifications = {
        "environment": args.env,
        "aws_region": args.region
    }

    print(f"\n🚀 Processing architecture diagram: {args.image}")
    print(f"Architecture name: {args.name}")
    print(f"Environment: {args.env}")
    print(f"Region: {args.region}\n")

    results = orchestrator.process_diagram(
        image_path=args.image,
        architecture_name=args.name,
        user_clarifications=user_clarifications,
        validate_terraform=not args.no_validate,
        run_security_scan=not args.no_security_scan
    )

    # Print results
    print("\n" + "=" * 60)
    print(f"Status: {results['status']}")
    print(f"Message: {results['message']}")
    print("=" * 60)

    if results.get("questions"):
        print("\n❓ Questions needing clarification:")
        for q in results["questions"]:
            print(f"  - {q}")

    if results.get("terraform_files"):
        print(f"\n📁 Generated files:")
        for f in results["terraform_files"]:
            print(f"  - {f}")
        print(f"\nOutput directory: {results['output_directory']}")

    if results.get("cost_breakdown"):
        print(f"\n💰 Cost breakdown:")
        for component, cost in results["cost_breakdown"].items():
            if isinstance(cost, (int, float)):
                print(f"  {component}: ${cost:.4f}")

    if results.get("validation_result"):
        validation = results["validation_result"]
        if validation["is_valid"]:
            print("\n✅ Terraform validation: PASSED")
        else:
            print("\n❌ Terraform validation: FAILED")
            for error in validation["errors"]:
                print(f"  ERROR: {error}")

    if results.get("security_result"):
        security = results["security_result"]
        print(f"\n🔒 Security scan:")
        print(f"  Passed checks: {security['passed_checks']}")
        print(f"  Failed checks: {security['failed_checks']}")
        print(f"  Severity breakdown: {security['severity_breakdown']}")

        if security["critical_issues"]:
            print(f"\n  Critical/High issues (showing first 10):")
            for issue in security["critical_issues"]:
                print(f"    - [{issue.get('severity')}] {issue.get('check_name', 'Unknown')}")

    print("\n" + "=" * 60)
    print(f"✨ Complete! Total cost: ${results['cost_breakdown'].get('total_usd', 0):.4f}")
    print("=" * 60 + "\n")
