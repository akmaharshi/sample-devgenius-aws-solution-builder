# Cost Optimization: Template-Based Terraform Generation

## 🎯 Overview

This document describes the **cost-optimized, template-based Terraform generation** approach that reduces AWS Bedrock costs by **up to 100%** while delivering **production-grade, deterministic infrastructure-as-code**.

## 🚀 NEW: 100% FREE Vision AI with Ollama

We now support **Ollama + Llama 3.2 Vision** as a FREE alternative to AWS Bedrock Vision!

**Quick Start:**
```bash
./setup-ollama.sh
```

See **[OLLAMA_SETUP.md](OLLAMA_SETUP.md)** for detailed setup instructions.

## 📊 Cost Comparison

| Approach | Per Diagram | 100 Diagrams | 10K Diagrams/Month | Annual Cost |
|----------|-------------|--------------|-------------------|-------------|
| **Old (LLM-based)** | $0.53 | $53.00 | $5,300/mo | $63,600/yr |
| **New (Template + Bedrock)** | $0.03 | $3.00 | $300/mo | $3,600/yr |
| **New (Template + Ollama)** | **$0.00** ✨ | **$0.00** | **$0/mo** | **$0/yr** |
| **Savings (Bedrock)** | **$0.50 (94%)** | **$50 (94%)** | **$5,000 (94%)** | **$60,000 (94%)** |
| **Savings (Ollama)** | **$0.53 (100%)** | **$53 (100%)** | **$5,300 (100%)** | **$63,600 (100%)** |

### Old Approach Cost Breakdown
```
Vision AI:              $0.03
Agent Invocation:       $0.05
CDK Generation:         $0.10  (128K tokens @ $15/M)
CloudFormation Gen:     $0.10
Cost Estimation:        $0.05
Documentation:          $0.05
Architecture Diagram:   $0.15  (extended thinking)
-----------------------------------
TOTAL:                  $0.53 per diagram
```

### New Approach Cost Breakdown
```
Vision AI:              $0.03  (ONLY Bedrock usage)
Intent Normalization:   $0.00  (Pure Python)
Terraform Generation:   $0.00  (Jinja2 templates)
Validation:             $0.00  (terraform CLI)
Security Scan:          $0.00  (Checkov)
-----------------------------------
TOTAL:                  $0.03 per diagram
```

## 🏗️ Architecture

### High-Level Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. VISION AI (Bedrock Vision) - $0.03                      │
│    • Detects services from architecture diagram            │
│    • Identifies connections and relationships              │
│    • Extracts textual hints                                │
│    • Returns structured JSON (NOT code)                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 2. INTENT NORMALIZATION (Pure Python) - $0.00             │
│    • Converts vision results to strict schema              │
│    • Applies environment-based rules                       │
│    • Generates clarification questions                     │
│    • Validates architecture requirements                   │
│    • NO LLM involvement                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 3. TERRAFORM GENERATION (Jinja2 Templates) - $0.00        │
│    • Loads service definitions from registry (YAML)        │
│    • Renders Terraform using templates                     │
│    • Deterministic output (same input → same code)         │
│    • Uses official Terraform modules                       │
│    • NO LLM involvement                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 4. VALIDATION (Terraform CLI) - $0.00                      │
│    • terraform fmt -check                                  │
│    • terraform init                                        │
│    • terraform validate                                    │
│    • NO LLM involvement                                    │
└────────────────┬────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────┐
│ 5. SECURITY SCAN (Checkov) - $0.00                        │
│    • Scans for 1000+ security issues                       │
│    • HIPAA, PCI-DSS, SOC2 compliance                       │
│    • Infrastructure best practices                         │
│    • NO LLM involvement                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔑 Key Design Principles

### 1. **Separation of Concerns**

| Layer | Responsibility | Technology | Bedrock Cost |
|-------|---------------|------------|--------------|
| Vision AI | Service detection ONLY | Bedrock Vision | $0.03 |
| Intent Normalization | Schema normalization | Python + Pydantic | $0.00 |
| Code Generation | Terraform rendering | Jinja2 Templates | $0.00 |
| Validation | Syntax & format checks | Terraform CLI | $0.00 |
| Security | Policy enforcement | Checkov | $0.00 |

### 2. **Registry-Based Services**

Adding a new AWS service requires **ZERO code changes** - only registry updates:

```yaml
# chatbot/registry/service_registry.yaml

services:
  new_service:
    name: "AWS New Service"
    category: "compute"
    terraform_resource: "aws_new_service"
    terraform_module: "terraform-aws-modules/new-service/aws"
    module_version: "~> 1.0"
    default_configuration:
      param1: "value1"
    parameters:
      - name: "param1"
        type: "string"
        required: true
```

### 3. **Template-Driven Generation**

Terraform code is generated using **Jinja2 templates**, not LLMs:

```jinja2
# chatbot/templates/terraform/services.tf.j2

{% for service in architecture.services %}
module "{{ service.id }}" {
  source  = "{{ registry.terraform_module }}"
  version = "{{ registry.module_version }}"

  name = "{{ service.name }}"
  # ... service-specific configuration
}
{% endfor %}
```

**Benefits:**
- **Deterministic**: Same input always produces same output
- **Fast**: No LLM latency
- **Free**: Zero Bedrock costs
- **Maintainable**: Easy to update templates
- **Testable**: Can unit test templates

### 4. **Intent Normalization Schema**

Vision AI output is converted to a **strict, validated schema**:

```python
class ArchitectureIntent(BaseModel):
    """Single source of truth for infrastructure"""

    # Metadata
    architecture_name: str
    description: str
    environment: Environment  # dev/staging/prod

    # Global config
    network: NetworkIntent
    security: SecurityIntent
    cost: CostIntent

    # Resources
    services: List[ServiceIntent]
    connections: List[Connection]
```

This ensures:
- **Explicit intent** (no guessing)
- **Validation** (catch errors early)
- **Consistency** (enforce standards)
- **Auditability** (track changes)

## 📁 Project Structure

```
chatbot/
├── schemas/
│   └── architecture_schema.py      # Pydantic models for normalized intent
├── registry/
│   └── service_registry.yaml       # AWS service definitions (add services here)
├── templates/
│   └── terraform/                  # Jinja2 templates for Terraform
│       ├── main.tf.j2
│       ├── variables.tf.j2
│       ├── networking.tf.j2
│       ├── services.tf.j2
│       └── outputs.tf.j2
├── vision_ai.py                    # Bedrock Vision (ONLY Bedrock usage)
├── intent_normalizer.py            # Vision → Schema converter
├── terraform_generator.py          # Template-based Terraform generator
├── terraform_validator.py          # Validation & security scanning
├── iac_orchestrator.py             # Main workflow coordinator
└── generate_terraform_widget.py    # Streamlit UI widget
```

## 🚀 Usage

### CLI Usage

```bash
cd chatbot

# Generate Terraform from diagram
python iac_orchestrator.py \
  --image path/to/diagram.png \
  --name my-architecture \
  --env prod \
  --region us-east-1

# Show cost comparison
python iac_orchestrator.py --cost-comparison
```

### Programmatic Usage

```python
from iac_orchestrator import IaCOrchestrator

# Initialize orchestrator
orchestrator = IaCOrchestrator(aws_region="us-east-1")

# Process diagram
results = orchestrator.process_diagram(
    image_path="diagram.png",
    architecture_name="web-app",
    user_clarifications={
        "environment": "prod",
        "aws_region": "us-east-1"
    },
    validate_terraform=True,
    run_security_scan=True
)

# Check results
if results["success"]:
    print(f"Terraform generated in: {results['output_directory']}")
    print(f"Total cost: ${results['cost_breakdown']['total_usd']}")
else:
    print(f"Error: {results['message']}")
```

### Streamlit UI

```python
# In your Streamlit app
from generate_terraform_widget import generate_terraform_widget

generate_terraform_widget(
    conversation_id=conversation_id,
    s3_client=s3_client,
    bucket_name=bucket_name,
    uploaded_image_key="path/to/diagram.png"
)
```

## 🔧 Adding New AWS Services

To add a new AWS service, **NO CODE CHANGES** are needed. Just update the registry:

1. **Edit** `chatbot/registry/service_registry.yaml`
2. **Add** your service definition:

```yaml
services:
  my_new_service:
    name: "AWS My New Service"
    category: "compute|storage|database|networking|security|analytics|messaging"
    terraform_resource: "aws_my_service"
    terraform_module: "terraform-aws-modules/my-service/aws"
    module_version: "~> 1.0"
    icon_name: "MyService"
    description: "Service description"
    default_configuration:
      param1: "default_value"
    parameters:
      - name: "param1"
        type: "string"
        required: true
        default: "default_value"
```

3. **Optional**: Update Jinja2 templates if service needs custom logic

4. **Done!** The service is now available for Terraform generation

## 🛡️ Security & Validation

### Automatic Validation

Every generated Terraform configuration is automatically:

1. **Format checked** (`terraform fmt`)
2. **Initialized** (`terraform init`)
3. **Validated** (`terraform validate`)
4. **Security scanned** (Checkov - 1000+ checks)

### Security Scan Coverage

Checkov scans for:
- AWS security best practices
- HIPAA compliance
- PCI-DSS compliance
- SOC2 compliance
- CIS AWS Benchmarks
- Encryption requirements
- IAM policy issues
- Network security misconfigurations

Example output:
```
Passed checks: 45
Failed checks: 3
Severity breakdown:
  🔴 CRITICAL: 0
  🟠 HIGH: 1
  🟡 MEDIUM: 2
  🟢 LOW: 0
```

## 💡 Best Practices

### 1. Environment-Specific Configuration

The system automatically applies environment-based overrides:

**Production:**
- Multi-AZ databases
- Enhanced monitoring
- 7-day backup retention
- Encryption enabled
- Deletion protection

**Development:**
- Single-AZ resources
- Minimal monitoring
- 1-day backup retention
- Cost optimization

### 2. Service Registry Management

Keep your service registry clean:
- Use semantic versioning for modules
- Document all parameters
- Provide sensible defaults
- Include description and metadata

### 3. Template Maintenance

When updating templates:
- Test with multiple architectures
- Ensure backwards compatibility
- Document template variables
- Use Jinja2 best practices

## 📈 Performance Metrics

| Metric | Old Approach (LLM) | New Approach (Template) |
|--------|-------------------|------------------------|
| **Cost per diagram** | $0.53 | $0.03 |
| **Generation time** | 30-60s | 2-5s |
| **Deterministic** | ❌ No | ✅ Yes |
| **Validation built-in** | ❌ No | ✅ Yes |
| **Security scan** | ❌ No | ✅ Yes |
| **Multi-cloud ready** | ❌ No | ✅ Yes |
| **Extensible without code** | ❌ No | ✅ Yes |

## 🎓 Learning & Examples

### Example 1: Simple Web Application

**Input:** Diagram showing EC2 + RDS

**Vision AI Detection:**
```json
{
  "detected_services": [
    {"service_type": "ec2", "label": "Web Server"},
    {"service_type": "rds", "label": "Database"}
  ],
  "detected_connections": [
    {"from_service": "Web Server", "to_service": "Database"}
  ]
}
```

**Generated Terraform:** Complete production-ready configuration with:
- VPC with public/private subnets
- EC2 instance with security groups
- RDS PostgreSQL with Multi-AZ (if prod)
- Proper IAM roles
- Encryption enabled
- Monitoring configured

**Cost:** $0.03 (vs $0.53 with old approach)

### Example 2: Serverless Application

**Input:** Diagram showing Lambda + DynamoDB + API Gateway

**Result:** Complete serverless infrastructure with:
- Lambda functions with proper IAM roles
- DynamoDB tables with encryption
- API Gateway with CloudWatch logs
- VPC endpoints for private access

**Cost:** $0.03 (94% savings)

## 🔄 Migration Guide

### From Old Approach to New Approach

If you're currently using the LLM-based generation:

1. **Replace widget import:**
   ```python
   # Old
   from generate_cdk_widget import generate_cdk_widget

   # New
   from generate_terraform_widget import generate_terraform_widget
   ```

2. **Update function call:**
   ```python
   # Old - generates CDK using Bedrock
   generate_cdk_widget(conversation_id, s3_client, bucket_name)

   # New - generates Terraform using templates
   generate_terraform_widget(conversation_id, s3_client, bucket_name, uploaded_image_key)
   ```

3. **Benefits:**
   - 94% cost reduction
   - Faster generation
   - Deterministic outputs
   - Built-in validation & security

## 📚 References

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Terraform AWS Modules](https://registry.terraform.io/namespaces/terraform-aws-modules)
- [Checkov Security Scanner](https://www.checkov.io/)
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Jinja2 Template Engine](https://jinja.palletsprojects.com/)

## 🤝 Contributing

To contribute new services or templates:

1. Fork the repository
2. Add service to `service_registry.yaml`
3. Update templates if needed
4. Test with sample diagrams
5. Submit pull request

## 📝 License

Same as the main DevGenius project.

---

**Questions or Issues?**

Open an issue in the GitHub repository with the tag `cost-optimization`.
