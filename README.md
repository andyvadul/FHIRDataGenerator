# FHIR Data Generator

A flexible tool for generating synthetic FHIR (Fast Healthcare Interoperability Resources) data with flattened column structures. Supports any FHIR resource type and multiple output formats.

## 📁 Project Structure

```
FHIRDataGenerator/
└── src/
    └── proto/
        ├── generate_fhir_data.py          # Main generator script
        ├── generate_fhir_data.jsonc       # Optional configuration file
        ├── requirements.txt               # Production dependencies
        ├── requirements-dev.txt           # Development dependencies
        └── README.md                      # This file
```

## 🎯 What It Does

The FHIR Data Generator automatically:

- **Discovers** all available FHIR resources dynamically (Patient, Observation, Encounter, etc.)
- **Flattens** complex nested FHIR schemas into tabular column structures
- **Generates** realistic synthetic data using intelligent field name patterns
- **Exports** to multiple formats: CSV, Parquet, or Parquet with ZSTD compression
- **Scales** from 10 records to 10M+ records with efficient processing

### Key Features

✅ **Resource Agnostic** - Works with any FHIR resource type  
✅ **Dynamic Discovery** - Automatically finds new resources in future FHIR versions  
✅ **Smart Data Generation** - Context-aware synthetic data based on field names  
✅ **Multiple Output Formats** - CSV, Parquet, Compressed Parquet  
✅ **Interactive Mode** - User-friendly prompts when no config provided  
✅ **Configurable Schema** - Control flattening depth, naming conventions, field exclusions  

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Navigate to the proto directory
cd src/proto/

# Install dependencies
pip install -r requirements.txt

# For development (includes testing, linting tools)
pip install -r requirements-dev.txt
```

### 2. Run Interactive Mode

```bash
python generate_fhir_data.py
```

This will guide you through:
- Selecting a FHIR resource from a paginated list
- Choosing output format (Parquet+ZSTD recommended)
- Selecting number of records (10, 100, 1K, 10K, 100K, 1M, 10M)

### 3. Using Configuration Files

Create a configuration file (recommended for repeated use):

```bash
# Copy the sample config
cp generate_fhir_data.jsonc.sample generate_fhir_data.jsonc

# Edit the config file
# Set resource_type, output format, record count, etc.

# Run with config by default the file with the same name as py file is picked up
python generate_fhir_data.py
```

## 📋 Configuration

### Automatic Config Discovery

If you don't specify a config file, the script looks for `generate_fhir_data.jsonc` in the same directory.

### Sample Configuration

```json
{
  "resource_type": "Patient",
  "output": {
    "format": "parquet+zstd",        // csv, parquet, or parquet+zstd
    "path": "",                      // Auto-generated if empty
    "count": 1000
  },
  "schema": {
    "separator": "_",                // Field separator for nested objects
    "case": "snake",                 // snake, camel, pascal, or as_is
    "max_depth": 3,                  // Maximum nesting levels
    "max_array_items": 3,            // Array expansion limit
    "exclude_fields": [              // Fields to skip
      "contained", "meta", "extension"
    ]
  },
  "fhir_version": "R4"               // R4 or R5
}
```

## 💻 Usage Examples

### Basic Usage

```bash
# Interactive mode - no config needed
python generate_fhir_data.py

# Use specific config file
python generate_fhir_data.py patient_config.jsonc
python generate_fhir_data.py observation_config.jsonc
```

### Example Workflows

```bash
# Generate 1000 patients with default settings
python generate_fhir_data.py

# Generate large observation dataset
python generate_fhir_data.py obs_config.jsonc

# Generate encounter data for testing
python generate_fhir_data.py encounter_config.jsonc
```

## 📊 Output Examples

### File Naming Convention

Generated files are automatically named with timestamps:

- **CSV**: `patient_synthetic_1000_20241201_143022.csv`
- **Parquet**: `observation_synthetic_10000_20241201_143025.parquet`  
- **Compressed**: `encounter_synthetic_100000_20241201_143028_zstd.parquet`

### Sample Output Structure

For a Patient resource, you might get columns like:
```
id, resource_type, active, gender, birth_date, 
name_0_given_0, name_0_family, telecom_0_value,
address_0_line_0, address_0_city, address_0_state,
address_0_postal_code, address_0_country, ...
```

## 🔧 Advanced Configuration

### Schema Control

```json
{
  "schema": {
    "separator": "_",                // Use "." for dot notation
    "case": "camel",                 // camelCase output
    "max_depth": 5,                  // Deeper nesting
    "max_array_items": 5,            // More array elements
    "include_fields": [              // Only include these root fields
      "id", "identifier", "name", "telecom"
    ],
    "exclude_fields": [              // Always exclude these
      "contained", "meta", "extension", "modifierExtension"
    ]
  }
}
```

### Output Control

```json
{
  "output": {
    "format": "parquet+zstd",        // Best compression
    "path": "custom_filename.parquet",
    "count": 1000000                 // 1M records
  }
}
```

## 🏥 Supported FHIR Resources

The tool dynamically discovers all available FHIR resources. Common examples include:

**Patient Management**: Patient, Person, RelatedPerson, Practitioner  
**Clinical**: Observation, Condition, Procedure, DiagnosticReport  
**Medication**: Medication, MedicationRequest, MedicationAdministration  
**Workflow**: Appointment, Encounter, CarePlan, Task  
**Administrative**: Organization, Location, HealthcareService  

Use the interactive mode to see all available resources for your FHIR version.

## 📈 Performance & Scale

### Record Count Options

- **10 records** - Quick testing
- **100 records** - Small datasets  
- **1,000 records** - Medium datasets (default)
- **10K records** - Large datasets
- **100K records** - Very large datasets
- **1M+ records** - Enterprise scale

### File Size Examples

| Records | Resource | Format | File Size | Generation Time |
|---------|----------|--------|-----------|----------------|
| 1K | Patient | CSV | ~200 KB | <1s |
| 1K | Patient | Parquet+ZSTD | ~50 KB | <1s |
| 100K | Patient | Parquet+ZSTD | ~2.5 MB | ~10s |
| 1M | Observation | Parquet+ZSTD | ~15 MB | ~90s |

## 🛠️ Development

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

### Code Quality

```bash
# Format code
black generate_fhir_data.py

# Lint code  
flake8 generate_fhir_data.py

# Type checking
mypy generate_fhir_data.py
```

## 📦 Dependencies

### Core Requirements

- **fhir.resources** - FHIR resource models
- **pandas** - Data manipulation and CSV export
- **pyarrow** - Parquet format support

### Optional

- **json5** - Enhanced JSON with comments (for .jsonc config files)

## ❓ Troubleshooting

### Common Issues

**"No FHIR resources discovered"**
```bash
pip install --upgrade fhir.resources
```

**"pyarrow not available"**
```bash
pip install pyarrow
```

**"Config file parsing error"**
- Remove comments if using standard JSON (not JSONC)
- Install json5: `pip install json5`

### Debug Mode

The script provides verbose output showing:
- Dependency availability
- Resource discovery process
- Schema generation progress
- File creation details

## 🎯 Use Cases

- **Healthcare Analytics** - Generate test datasets for analysis
- **Application Testing** - Create realistic FHIR data for testing
- **ML/AI Training** - Synthetic datasets for model development
- **Schema Exploration** - Understand FHIR resource structures
- **Integration Testing** - Test data pipeline with various FHIR resources

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues, feature requests, or questions:
- Check existing issues in the repository
- Create a new issue with detailed description
- Include sample config files and error messages

---

**Quick Commands Summary:**
```bash
# Setup
pip install -r requirements.txt

# Interactive run
python generate_fhir_data.py

# Config-based run  
python generate_fhir_data.py my_config.jsonc
```