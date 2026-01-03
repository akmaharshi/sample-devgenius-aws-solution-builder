# Terraform Generation Features - DevGenius

## Overview

DevGenius now includes advanced Terraform generation capabilities with diagram parsing, modular code structure, and automatic security vulnerability detection and remediation.

## Phase 1: Diagram Parsing & Modular Terraform Generation ✅

### Supported Diagram Formats

The system can now accept and parse infrastructure diagrams in multiple formats:

- **Image Formats**: PNG, JPEG, GIF, BMP, WebP
- **draw.io**: `.drawio`, `.xml` files
- **Lucid Charts**: `.lucid`, `.lucidchart` files (export as PNG/draw.io for full support)
- **Microsoft Visio**: `.vsdx`, `.vsd` files

### Diagram Parsing Capabilities

#### AI-Powered Image Analysis
- Uses Claude Vision (via Amazon Bedrock) to analyze architecture diagrams
- Extracts AWS services and components
- Identifies relationships and connections
- Determines data flow patterns
- Recognizes network architecture (VPCs, subnets, security groups)

#### draw.io XML Parsing
- Parses native draw.io XML format
- Extracts components and connections
- Identifies AWS service types from labels and styles
- Maintains relationship mappings

### Modular Terraform Structure

When generating Terraform code, DevGenius creates a professional, production-ready modular structure:

```
terraform-infrastructure/
├── main.tf                  # Main configuration with module calls
├── variables.tf             # Input variables
├── outputs.tf               # Output values
├── terraform.tfvars.example # Example variable values
├── backend.tf               # Remote state configuration
└── modules/
    ├── vpc/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── ec2/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    ├── s3/
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── README.md
    └── ...
```

### Module Features

Each generated module includes:
- **Comprehensive Comments**: Explains what each resource does
- **Input Validation**: Validates variable inputs
- **Default Values**: Sensible defaults for optional parameters
- **Outputs**: Exposes necessary values for other modules
- **README**: Documentation for module usage
- **Best Practices**: Follows Terraform and AWS best practices

## Phase 2: Security Vulnerability Detection & Auto-Fix ✅

### Security Scanning Engine

The Terraform Security Scanner performs comprehensive security analysis:

#### Supported Resource Types

1. **S3 Buckets** (`aws_s3_bucket`)
   - Missing encryption
   - Public access controls
   - Versioning disabled
   - Missing lifecycle policies

2. **Security Groups** (`aws_security_group`)
   - Open ingress rules (0.0.0.0/0)
   - Unrestricted egress
   - Missing descriptions

3. **RDS Instances** (`aws_db_instance`)
   - Public accessibility
   - Missing encryption
   - No automated backups
   - Weak authentication

4. **EC2 Instances** (`aws_instance`)
   - Missing detailed monitoring
   - Public IP assignment
   - Unencrypted EBS volumes
   - Missing IMDSv2 enforcement

5. **IAM Policies** (`aws_iam_policy`)
   - Wildcard actions (*)
   - Wildcard resources (*)
   - Overly permissive policies

6. **Lambda Functions** (`aws_lambda_function`)
   - Missing X-Ray tracing
   - Not in VPC
   - Missing dead letter queue
   - Overly permissive IAM roles

### Vulnerability Severity Levels

- **CRITICAL** 🔴: Immediate security risk (public access, no encryption)
- **HIGH** 🟠: Significant security concern (wildcard permissions)
- **MEDIUM** 🟡: Important best practice (missing monitoring)
- **LOW** 🔵: Minor improvement (missing tags)

### Automatic Remediation

The system automatically fixes detected vulnerabilities:

#### Example: S3 Bucket Security

**Before (Insecure)**:
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"
}
```

**After (Secure)**:
```hcl
resource "aws_s3_bucket" "data" {
  bucket = "my-data-bucket"

  # Auto-added encryption
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  # Auto-added public access block
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  # Auto-added versioning
  versioning {
    enabled = true
  }
}
```

#### Example: RDS Instance Security

**Before (Insecure)**:
```hcl
resource "aws_db_instance" "main" {
  identifier     = "mydb"
  engine         = "mysql"
  publicly_accessible = true
}
```

**After (Secure)**:
```hcl
resource "aws_db_instance" "main" {
  identifier     = "mydb"
  engine         = "mysql"
  publicly_accessible = false  # Auto-fixed
  storage_encrypted   = true   # Auto-added
  backup_retention_period = 7  # Auto-added
}
```

### Security Report

After scanning, a comprehensive security report is generated:

```markdown
# Terraform Security Scan Report

**Total Vulnerabilities Found:** 15
**Automatically Fixed:** 12

## Severity Summary
- **CRITICAL**: 3
- **HIGH**: 5
- **MEDIUM**: 4
- **LOW**: 3

## Detailed Findings

### 1. S3 bucket does not have server-side encryption enabled
- **Resource**: `aws_s3_bucket.data`
- **Severity**: HIGH
- **CWE**: CWE-311: Missing Encryption of Sensitive Data
- **Fix**: Add server_side_encryption_configuration block

### 2. Security group allows ingress from 0.0.0.0/0
- **Resource**: `aws_security_group.web`
- **Severity**: CRITICAL
- **CWE**: CWE-284: Improper Access Control
- **Fix**: Restrict ingress to specific IP ranges

...

## Auto-Applied Fixes
- **aws_s3_bucket.data**: Added server_side_encryption_configuration
- **aws_s3_bucket.data**: Enabled public access blocking
- **aws_db_instance.main**: Set publicly_accessible = false
- **aws_db_instance.main**: Enabled storage encryption
...
```

## Usage

### In the DevGenius UI

1. Navigate to the "Build a solution" or "Modify your existing architecture" tab
2. Describe your architecture or upload a diagram
3. Go to the "Terraform code" tab
4. Check the options:
   - ✅ **Generate Terraform code**
   - 🏗️ **Modular structure** (recommended)
   - 🔒 **Security scanning & auto-fix** (recommended)
5. Click generate

### The system will:

1. 🔄 Generate modular Terraform code based on the architecture
2. 🔍 Scan for security vulnerabilities
3. 🔧 Automatically fix detected issues
4. 📊 Show security metrics and severity counts
5. 📄 Provide both the code and security report
6. 📥 Allow download of the complete project

### Security Metrics Display

After generation, you'll see:

```
🔴 CRITICAL     🟠 HIGH        🟡 MEDIUM      🔵 LOW
     3             5              4             3
```

And a success message:
```
✅ Automatically fixed 12 vulnerabilities!
```

## API Reference

### DiagramParser Class

```python
from diagram_parser import DiagramParser

# Initialize parser
parser = DiagramParser()

# Parse diagram
result = parser.parse_diagram(
    file_path="architecture.png",
    file_content=image_bytes
)

# Generate Terraform structure
terraform_files = parser.generate_terraform_structure(result)
```

### TerraformSecurityScanner Class

```python
from terraform_security import TerraformSecurityScanner

# Initialize scanner
scanner = TerraformSecurityScanner()

# Scan code
vulnerabilities = scanner.scan_terraform_code(terraform_code)

# Auto-fix
fixed_code, applied_fixes = scanner.auto_fix_vulnerabilities(
    terraform_code,
    vulnerabilities
)

# Generate report
report = scanner.generate_security_report(
    vulnerabilities,
    applied_fixes
)
```

## Security Rules Database

The scanner includes rules for detecting:

### CWE Coverage

- **CWE-284**: Improper Access Control
- **CWE-269**: Improper Privilege Management
- **CWE-311**: Missing Encryption of Sensitive Data
- **CWE-668**: Exposure of Resource to Wrong Sphere
- **CWE-693**: Protection Mechanism Failure
- **CWE-778**: Insufficient Logging
- **CWE-657**: Violation of Secure Design Principles

### Compliance Frameworks

Generated code helps meet requirements for:
- **AWS Well-Architected Framework**
- **CIS AWS Foundations Benchmark**
- **NIST Cybersecurity Framework**
- **SOC 2 Compliance**
- **HIPAA Security Rule**
- **PCI DSS**

## Benefits

### For Developers
- ⚡ **Faster Development**: Generate production-ready code in seconds
- 🏗️ **Best Practices**: Modular structure following Terraform conventions
- 🔒 **Security by Default**: Automatic vulnerability fixes
- 📚 **Learning Tool**: See how to properly structure Terraform projects

### For Security Teams
- 🛡️ **Proactive Security**: Catch issues before deployment
- 📊 **Visibility**: Comprehensive security reports
- ✅ **Compliance**: Meet security standards automatically
- 🔄 **Continuous Improvement**: Updated security rules

### For DevOps Teams
- 🚀 **Rapid Deployment**: Complete infrastructure in minutes
- 📦 **Reusable Modules**: Standardized, tested components
- 🔄 **GitOps Ready**: Version-controlled infrastructure
- 📖 **Documentation**: Auto-generated module docs

## Future Enhancements

### Planned Features
- Cost optimization suggestions
- Performance tuning recommendations
- Multi-cloud support (Azure, GCP)
- Terraform state management
- CI/CD pipeline generation
- Infrastructure testing (Terratest)
- Drift detection
- Resource tagging strategies
- Compliance policy enforcement

## Support

For issues, feature requests, or questions:
- Create an issue in the GitHub repository
- Refer to the main README.md
- Check Terraform documentation: https://www.terraform.io/docs

---

**DevGenius - Infrastructure as Code, Made Intelligent**
