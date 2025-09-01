#!/usr/bin/env python3
"""
Config-Driven FHIR Resource Data Generator

Generate synthetic data for any FHIR resource type with flattened column structure.
Uses configuration files or interactive prompts.

Requirements:
  pip install fhir.resources pandas pyarrow

Usage:
  python generate_fhir_data.py config.jsonc
  python generate_fhir_data.py                    # Interactive mode
"""

import argparse
import importlib
import json
import sys
import warnings
import math
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, get_args, get_origin
import random
import uuid

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

print(f"🔬 Config-Driven FHIR Resource Data Generator")
print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ---- Dependency Management ----
def check_required_dependencies():
    """Check and import required dependencies."""
    missing = []
    
    try:
        import fhir.resources
        print("✅ fhir.resources available")
    except ImportError:
        missing.append("fhir.resources")
    
    try:
        import pandas as pd
        print("✅ pandas available")
    except ImportError:
        missing.append("pandas")
    
    try:
        import pyarrow as pa
        print("✅ pyarrow available (parquet support)")
    except ImportError:
        print("⚠️  pyarrow not available - parquet formats disabled")
    
    if missing:
        print(f"\n❌ Missing required dependencies: {', '.join(missing)}")
        print("Install with: pip install " + " ".join(missing))
        sys.exit(1)
    
    return True

# ---- Configuration Management ----
def load_json_config(config_path: str) -> Dict[str, Any]:
    """Load configuration with JSON5/JSONC support."""
    config_file = Path(config_path)
    
    if not config_file.exists():
        return None
    
    try:
        # Try json5 first for comment support
        try:
            import json5
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json5.load(f)
            print(f"✅ Config loaded from {config_path} (with json5)")
            return config
        except ImportError:
            # Fallback to regular json
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Simple comment removal for basic JSONC support
                lines = []
                for line in content.split('\n'):
                    # Remove single line comments
                    if '//' in line:
                        line = line.split('//')[0]
                    lines.append(line)
                cleaned_content = '\n'.join(lines)
                config = json.loads(cleaned_content)
            print(f"✅ Config loaded from {config_path} (basic JSONC support)")
            return config
            
    except Exception as e:
        print(f"❌ Failed to parse config file {config_path}: {e}")
        return None

def find_default_config(script_name: str) -> Optional[str]:
    """Find default config file with same name as script."""
    script_path = Path(script_name)
    config_path = script_path.with_suffix('.jsonc')
    
    if config_path.exists():
        return str(config_path)
    
    # Also try .json extension
    json_path = script_path.with_suffix('.json')
    if json_path.exists():
        return str(json_path)
    
    return None

def create_default_config() -> Dict[str, Any]:
    """Create default configuration."""
    return {
        "resource_type": "",
        "output": {
            "format": "parquet+zstd",
            "path": "",
            "count": 1000
        },
        "schema": {
            "separator": "_",
            "case": "snake",
            "max_depth": 3,
            "max_array_items": 3,
            "include_fields": [],
            "exclude_fields": ["contained", "meta", "extension", "modifierExtension"]
        },
        "fhir_version": "R4"
    }

# ---- FHIR Resource Discovery ----
def discover_fhir_resources(fhir_version: str = "R4") -> Dict[str, Any]:
    """Dynamically discover all available FHIR resources from the library."""
    resources = {}
    
    # Possible base module paths to try
    base_modules = [
        "fhir.resources",
        f"fhir.resources.{fhir_version.lower()}",
        f"fhir.resources{fhir_version.upper()}"
    ]
    
    print("🔍 Dynamically discovering FHIR resources...")
    
    for base_module_name in base_modules:
        try:
            # Import the base module
            base_module = importlib.import_module(base_module_name)
            print(f"   Scanning {base_module_name}...")
            
            # Get all attributes from the module
            if hasattr(base_module, '__all__'):
                # Use __all__ if available (explicit exports)
                potential_resources = base_module.__all__
                print(f"   Found __all__ with {len(potential_resources)} items")
            else:
                # Fallback: scan directory structure
                module_dir = Path(base_module.__file__).parent
                potential_resources = []
                
                # Look for Python files that might be resources
                for py_file in module_dir.glob("*.py"):
                    if py_file.name.startswith('_'):
                        continue
                    name = py_file.stem
                    # Convert snake_case to PascalCase for resource names
                    resource_name = ''.join(word.capitalize() for word in name.split('_'))
                    potential_resources.append(resource_name)
                
                print(f"   Found {len(potential_resources)} potential resources from directory scan")
            
            # Test each potential resource
            for resource_name in potential_resources:
                try:
                    # Try to import the specific resource module
                    module_path = f"{base_module_name}.{resource_name.lower()}"
                    resource_module = importlib.import_module(module_path)
                    
                    # Look for a class with the same name as the resource
                    resource_class = getattr(resource_module, resource_name, None)
                    
                    # Validate it's a proper FHIR resource (has Pydantic fields)
                    if (resource_class and 
                        isinstance(resource_class, type) and
                        (hasattr(resource_class, '__fields__') or hasattr(resource_class, 'model_fields'))):
                        
                        # Additional check: ensure it's actually a FHIR resource
                        # by checking if it has a resourceType or similar FHIR characteristics
                        fields = get_model_fields(resource_class)
                        if fields and len(fields) > 3:  # Real FHIR resources have many fields
                            resources[resource_name] = {
                                'class': resource_class,
                                'module': module_path,
                                'field_count': len(fields)
                            }
                            
                except (ImportError, AttributeError, TypeError):
                    # Resource doesn't exist or isn't importable, skip silently
                    continue
            
            # If we found resources in this base module, we're done
            if resources:
                print(f"✅ Successfully discovered {len(resources)} resources from {base_module_name}")
                break
                
        except ImportError:
            print(f"   ⚠️  Could not import {base_module_name}")
            continue
    
    # Fallback: try direct introspection of the main fhir.resources package
    if not resources:
        print("   🔄 Trying direct package introspection...")
        try:
            import pkgutil
            import fhir.resources as fr_package
            
            # Walk through all modules in the package
            for importer, modname, ispkg in pkgutil.iter_modules(fr_package.__path__, fr_package.__name__ + "."):
                if ispkg:
                    continue
                    
                try:
                    module = importlib.import_module(modname)
                    # Look for classes that look like FHIR resources
                    for attr_name in dir(module):
                        if attr_name.startswith('_'):
                            continue
                            
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            (hasattr(attr, '__fields__') or hasattr(attr, 'model_fields'))):
                            
                            fields = get_model_fields(attr)
                            if fields and len(fields) > 3:
                                resources[attr_name] = {
                                    'class': attr,
                                    'module': modname,
                                    'field_count': len(fields)
                                }
                                
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"   ❌ Package introspection failed: {e}")
    
    if resources:
        print(f"✅ Total discovered: {len(resources)} FHIR resources")
        # Show a few examples
        sample_resources = sorted(list(resources.keys()))[:5]
        print(f"   Examples: {', '.join(sample_resources)}{'...' if len(resources) > 5 else ''}")
    else:
        print("❌ No FHIR resources discovered")
    
    return resources

# ---- Interactive Interface ----
def paginated_selection(items: List[str], items_per_page: int = 20, title: str = "Select an option") -> str:
    """Display paginated list and get user selection."""
    total_pages = math.ceil(len(items) / items_per_page)
    current_page = 1
    
    while True:
        print(f"\n{title}")
        print("=" * 60)
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(items))
        
        # Display current page items
        for i in range(start_idx, end_idx):
            print(f"{i + 1:3d}. {items[i]}")
        
        print(f"\nPage {current_page} of {total_pages}")
        
        # Navigation options
        nav_options = []
        if current_page > 1:
            nav_options.append("p) Previous page")
        if current_page < total_pages:
            nav_options.append("n) Next page")
        nav_options.append("q) Quit")
        
        if nav_options:
            print("Navigation: " + " | ".join(nav_options))
        
        choice = input(f"\nEnter number (1-{len(items)}) or navigation option: ").strip().lower()
        
        # Handle navigation
        if choice == 'p' and current_page > 1:
            current_page -= 1
            continue
        elif choice == 'n' and current_page < total_pages:
            current_page += 1
            continue
        elif choice == 'q':
            print("👋 Goodbye!")
            sys.exit(0)
        
        # Handle selection
        try:
            selection_num = int(choice)
            if 1 <= selection_num <= len(items):
                return items[selection_num - 1]
            else:
                print(f"❌ Please enter a number between 1 and {len(items)}")
        except ValueError:
            print("❌ Please enter a valid number or navigation option")

def select_output_format() -> str:
    """Interactive output format selection."""
    formats = [
        ("parquet+zstd", "Parquet with ZSTD compression (recommended, smallest files)"),
        ("parquet", "Uncompressed Parquet (fast, larger files)"),
        ("csv", "Comma-separated values (universal compatibility)")
    ]
    
    print("\n📁 Select Output Format")
    print("=" * 60)
    
    for i, (format_key, description) in enumerate(formats, 1):
        print(f"{i}. {description}")
    
    while True:
        choice = input(f"\nSelect format (1-{len(formats)}) [1]: ").strip()
        
        if choice == "" or choice == "1":
            return formats[0][0]  # Default to parquet+zstd
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(formats):
                return formats[choice_num - 1][0]
            else:
                print(f"❌ Please enter a number between 1 and {len(formats)}")
        except ValueError:
            print("❌ Please enter a valid number")

def select_record_count() -> int:
    """Interactive record count selection."""
    count_options = [
        (10, "10 records (quick test)"),
        (100, "100 records (small dataset)"),
        (1000, "1,000 records (medium dataset)"),
        (10000, "10K records (large dataset)"),
        (100000, "100K records (very large)"),
        (1000000, "1M records (massive dataset)"),
        (10000000, "10M records (enterprise scale)")
    ]
    
    print("\n📊 Select Number of Records")
    print("=" * 60)
    
    for i, (count, description) in enumerate(count_options, 1):
        print(f"{i}. {description}")
    
    while True:
        choice = input(f"\nSelect count (1-{len(count_options)}) [3]: ").strip()
        
        if choice == "" or choice == "3":
            return count_options[2][0]  # Default to 1000
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(count_options):
                return count_options[choice_num - 1][0]
            else:
                print(f"❌ Please enter a number between 1 and {len(count_options)}")
        except ValueError:
            print("❌ Please enter a valid number")

def interactive_config_creation(resources: Dict[str, Any]) -> Dict[str, Any]:
    """Create configuration through interactive prompts."""
    print("\n🔧 Interactive Configuration Setup")
    print("=" * 60)
    print("No configuration file found. Let's set up your FHIR data generation:")
    
    # Select resource
    resource_names = sorted(list(resources.keys()))
    selected_resource = paginated_selection(resource_names, 15, "🏥 Select FHIR Resource Type")
    
    # Select output format
    output_format = select_output_format()
    
    # Select record count
    record_count = select_record_count()
    
    # Create config
    config = create_default_config()
    config["resource_type"] = selected_resource
    config["output"]["format"] = output_format
    config["output"]["count"] = record_count
    
    print(f"\n✅ Configuration Summary:")
    print(f"   Resource: {selected_resource}")
    print(f"   Format: {output_format}")
    print(f"   Count: {record_count:,} records")
    
    return config

# ---- Type System and Field Analysis (same as before) ----
def get_model_fields(model_cls) -> Dict[str, Any]:
    """Extract fields from Pydantic model."""
    try:
        if hasattr(model_cls, '__fields__'):
            return model_cls.__fields__
        elif hasattr(model_cls, 'model_fields'):
            return model_cls.model_fields
        else:
            return {}
    except Exception:
        return {}

def get_field_type(field_info) -> Any:
    """Extract field type from field info."""
    try:
        if hasattr(field_info, 'outer_type_'):
            return field_info.outer_type_
        elif hasattr(field_info, 'annotation'):
            return field_info.annotation
        elif hasattr(field_info, 'type_'):
            return field_info.type_
        else:
            return Any
    except Exception:
        return Any

def is_pydantic_model(cls: Any) -> bool:
    """Check if class is a Pydantic model."""
    try:
        from pydantic import BaseModel
        return isinstance(cls, type) and issubclass(cls, BaseModel)
    except Exception:
        return False

def unwrap_optional_and_list(field_type) -> Tuple[bool, bool, Any]:
    """Returns (is_optional, is_list, inner_type)"""
    is_optional = False
    is_list = False
    inner_type = field_type
    
    origin = get_origin(field_type)
    args = get_args(field_type)
    
    if origin is Union:
        non_none_args = [arg for arg in args if arg != type(None)]
        if len(non_none_args) == 1:
            is_optional = True
            inner_type = non_none_args[0]
            _, is_list, inner_type = unwrap_optional_and_list(inner_type)
        else:
            inner_type = non_none_args[0] if non_none_args else field_type
    
    origin = get_origin(inner_type)
    if origin in (list, List):
        is_list = True
        args = get_args(inner_type)
        if args:
            inner_type = args[0]
            is_optional_elem, _, inner_type = unwrap_optional_and_list(inner_type)
    
    return is_optional, is_list, inner_type

def is_primitive_type(type_hint) -> bool:
    """Check if type is primitive."""
    primitives = (str, int, float, bool, type(None))
    
    if type_hint in primitives:
        return True
    
    origin = get_origin(type_hint)
    if origin is Union:
        return all(is_primitive_type(arg) for arg in get_args(type_hint))
    
    return False

# ---- Flattening Logic ----
def flatten_schema(model_cls, config: Dict[str, Any], prefix: str = "", depth: int = 0) -> List[str]:
    """Flatten FHIR resource schema into column names."""
    schema_config = config.get('schema', {})
    
    if depth >= schema_config.get('max_depth', 3):
        return []
    
    separator = schema_config.get('separator', '_')
    case_style = schema_config.get('case', 'snake')
    exclude_fields = set(schema_config.get('exclude_fields', []))
    include_fields = set(schema_config.get('include_fields', []))
    max_array_items = schema_config.get('max_array_items', 3)
    
    columns = []
    fields = get_model_fields(model_cls)
    
    for field_name, field_info in fields.items():
        if field_name in exclude_fields:
            continue
        
        if include_fields and depth == 0 and field_name not in include_fields:
            continue
        
        field_type = get_field_type(field_info)
        is_optional, is_list, inner_type = unwrap_optional_and_list(field_type)
        
        if prefix:
            column_base = f"{prefix}{separator}{field_name}"
        else:
            column_base = field_name
        
        column_name = apply_case_style(column_base, case_style)
        
        if is_list:
            if is_primitive_type(inner_type):
                for i in range(max_array_items):
                    indexed_name = apply_case_style(f"{column_base}{separator}{i}", case_style)
                    columns.append(indexed_name)
            else:
                for i in range(max_array_items):
                    indexed_prefix = f"{column_base}{separator}{i}"
                    if is_pydantic_model(inner_type):
                        columns.extend(flatten_schema(inner_type, config, indexed_prefix, depth + 1))
                    else:
                        columns.append(apply_case_style(indexed_prefix, case_style))
        else:
            if is_pydantic_model(inner_type):
                columns.extend(flatten_schema(inner_type, config, column_base, depth + 1))
            else:
                columns.append(column_name)
    
    return columns

def apply_case_style(name: str, style: str) -> str:
    """Apply naming case style."""
    if style == 'snake':
        return to_snake_case(name)
    elif style == 'camel':
        return to_camel_case(name)
    elif style == 'pascal':
        return to_pascal_case(name)
    else:
        return name

def to_snake_case(name: str) -> str:
    """Convert to snake_case."""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0 and (name[i-1].islower() or (i+1 < len(name) and name[i+1].islower())):
            result.append('_')
        result.append(char.lower())
    return ''.join(result)

def to_camel_case(name: str) -> str:
    """Convert to camelCase."""
    name = to_snake_case(name)
    parts = name.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

def to_pascal_case(name: str) -> str:
    """Convert to PascalCase."""
    name = to_snake_case(name)
    return ''.join(word.capitalize() for word in name.split('_'))

# ---- Dynamic Data Generation ----
class FHIRDataGenerator:
    """Generate realistic synthetic FHIR data."""
    
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        self.counter = 0
        self.used_ids = set()
    
    def generate_value(self, column_name: str) -> Any:
        """Generate synthetic data based on column name patterns."""
        self.counter += 1
        col = column_name.lower()
        
        if col == 'id' or col.endswith('_id'):
            base_id = f"{self.resource_name.lower()}-{self.counter:06d}"
            while base_id in self.used_ids:
                self.counter += 1
                base_id = f"{self.resource_name.lower()}-{self.counter:06d}"
            self.used_ids.add(base_id)
            return base_id
        
        if col == 'resource_type':
            return self.resource_name
        
        if any(term in col for term in ['identifier', 'uuid', 'reference']):
            return str(uuid.uuid4())
        
        if 'status' in col:
            if self.resource_name == 'Patient':
                return random.choice(['active', 'inactive', 'entered-in-error'])
            elif self.resource_name == 'Observation':
                return random.choice(['final', 'preliminary', 'amended'])
            else:
                return random.choice(['active', 'inactive', 'completed', 'draft'])
        
        if any(term in col for term in ['active', 'deceased', 'implicit_rules']):
            return random.choice([True, False])
        
        if 'date' in col or 'time' in col:
            if 'birth' in col:
                year = random.randint(1920, 2020)
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                return f"{year:04d}-{month:02d}-{day:02d}"
            else:
                return datetime.now().date().isoformat()
        
        if 'given' in col or 'first' in col:
            return random.choice(['John', 'Jane', 'Michael', 'Sarah', 'David', 'Lisa', 'Robert', 'Mary', 'James', 'Jennifer'])
        
        if 'family' in col or 'last' in col:
            return random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis'])
        
        if 'email' in col:
            names = ['john', 'jane', 'mike', 'sarah']
            domains = ['example.com', 'test.org', 'demo.net']
            return f"{random.choice(names)}{self.counter}@{random.choice(domains)}"
        
        if 'phone' in col:
            return f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}"
        
        if 'line' in col or 'street' in col:
            return f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'First', 'Second'])} St"
        
        if 'city' in col:
            return random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia'])
        
        if 'state' in col:
            return random.choice(['NY', 'CA', 'IL', 'TX', 'AZ', 'PA'])
        
        if 'postal' in col or 'zip' in col:
            return f"{random.randint(10000, 99999)}"
        
        if 'country' in col:
            return random.choice(['US', 'CA', 'GB', 'AU'])
        
        if 'gender' in col:
            return random.choice(['male', 'female', 'other', 'unknown'])
        
        if 'language' in col:
            return random.choice(['en', 'es', 'fr', 'de'])
        
        if 'system' in col:
            return 'http://terminology.hl7.org/CodeSystem/v3-ActCode'
        
        if 'code' in col:
            return f"CODE-{random.randint(1000, 9999)}"
        
        if 'display' in col:
            return f"Display Text {self.counter}"
        
        if 'value' in col and ('quantity' in col or 'integer' in col):
            return random.randint(1, 100)
        
        if any(term in col for term in ['text', 'description', 'note']):
            return f"Sample text content {self.counter}"
        
        if 'url' in col:
            return f"https://example.com/resource/{self.counter}"
        
        if 'version' in col:
            return f"1.{random.randint(0, 9)}.{random.randint(0, 9)}"
        
        if any(term in col for term in ['name', 'title']):
            return f"Sample {self.resource_name} {self.counter}"
        
        return ""

# ---- Output Format Handlers ----
def save_data(data: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Save data in the specified format."""
    import pandas as pd
    
    if not data:
        print("❌ No data to save")
        return ""
    
    output_config = config.get('output', {})
    format_type = output_config.get('format', 'parquet+zstd')
    
    # Generate output path if not specified
    output_path = output_config.get('path', '')
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        resource_name = config['resource_type'].lower()
        count = len(data)
        
        if format_type == 'csv':
            ext = 'csv'
            suffix = ''
        elif format_type == 'parquet':
            ext = 'parquet'
            suffix = ''
        elif format_type == 'parquet+zstd':
            ext = 'parquet'
            suffix = '_zstd'
        else:
            ext = 'parquet'
            suffix = ''
        
        output_path = f"{resource_name}_synthetic_{count}_{timestamp}{suffix}.{ext}"
    
    df = pd.DataFrame(data)
    
    if format_type == 'csv':
        df.to_csv(output_path, index=False)
        print(f"💾 Saved {len(data):,} records to {output_path} (CSV)")
    elif format_type == 'parquet':
        df.to_parquet(output_path, index=False, engine='pyarrow')
        print(f"💾 Saved {len(data):,} records to {output_path} (Parquet)")
    elif format_type == 'parquet+zstd':
        df.to_parquet(output_path, index=False, engine='pyarrow', compression='zstd')
        print(f"💾 Saved {len(data):,} records to {output_path} (Parquet + ZSTD)")
    else:
        raise ValueError(f"Unsupported format: {format_type}")
    
    return output_path

# ---- Main Application ----
def main():
    parser = argparse.ArgumentParser(
        description="Config-driven FHIR resource data generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s config.jsonc              # Use specific config file
  %(prog)s                           # Interactive mode (looks for script_name.jsonc)
        """
    )
    
    parser.add_argument('config', nargs='?', help='Configuration file path (JSONC/JSON)')
    
    args = parser.parse_args()
    
    # Check dependencies
    check_required_dependencies()
    
    # Load or create configuration
    config = None
    
    if args.config:
        # User provided config file
        config = load_json_config(args.config)
        if config is None:
            print(f"❌ Could not load config file: {args.config}")
            sys.exit(1)
    else:
        # Look for default config file
        script_name = sys.argv[0]
        default_config_path = find_default_config(script_name)
        
        if default_config_path:
            print(f"📋 Found default config: {default_config_path}")
            config = load_json_config(default_config_path)
        
        if config is None:
            # Show warning and use interactive mode
            print("⚠️  No configuration file provided or found.")
            print(f"💡 Tip: Create a '{Path(script_name).stem}.jsonc' file in the same directory for automatic loading.")
            
            # Discover resources for interactive mode
            print(f"\n🔍 Discovering FHIR resources...")
            resources = discover_fhir_resources()
            
            if not resources:
                print("❌ No FHIR resources found. Please check your fhir.resources installation.")
                sys.exit(1)
            
            print(f"✅ Found {len(resources)} FHIR resources")
            
            # Interactive configuration
            config = interactive_config_creation(resources)
    
    # Validate required config
    if not config.get('resource_type'):
        print("❌ Configuration missing 'resource_type'")
        sys.exit(1)
    
    # Load FHIR resources if not already loaded
    if 'resources' not in locals():
        fhir_version = config.get('fhir_version', 'R4')
        print(f"🔍 Loading FHIR {fhir_version} resources...")
        resources = discover_fhir_resources(fhir_version)
        
        if not resources:
            print(f"❌ No FHIR {fhir_version} resources found")
            sys.exit(1)
        
        print(f"✅ Loaded {len(resources)} FHIR resources")
    
    # Validate resource exists
    resource_type = config['resource_type']
    if resource_type not in resources:
        print(f"❌ Resource '{resource_type}' not found in available FHIR resources")
        print(f"💡 Available resources: {', '.join(sorted(resources.keys())[:10])}...")
        sys.exit(1)
    
    resource_class = resources[resource_type]['class']
    print(f"✅ Using {resource_type} from {resources[resource_type]['module']}")
    
    # Generate schema
    print(f"📊 Analyzing {resource_type} schema...")
    columns = flatten_schema(resource_class, config)
    
    if not columns:
        print(f"❌ No columns generated for {resource_type}")
        sys.exit(1)
    
    # Remove duplicates while preserving order
    unique_columns = []
    seen = set()
    for col in columns:
        if col not in seen:
            seen.add(col)
            unique_columns.append(col)
    
    print(f"✅ Generated {len(unique_columns)} unique columns")
    
    # Generate data
    output_config = config.get('output', {})
    record_count = output_config.get('count', 1000)
    
    print(f"🎲 Generating {record_count:,} {resource_type} records...")
    generator = FHIRDataGenerator(resource_type)
    
    data = []
    for i in range(record_count):
        if i > 0 and i % 10000 == 0:
            print(f"   Generated {i:,} records...")
        
        record = {}
        for col in unique_columns:
            record[col] = generator.generate_value(col)
        data.append(record)
    
    # Save data
    output_path = save_data(data, config)
    
    # Summary
    if output_path:
        file_size = Path(output_path).stat().st_size
        print(f"\n📈 Generation Complete!")
        print(f"   Resource Type: {resource_type}")
        print(f"   Records: {record_count:,}")
        print(f"   Columns: {len(unique_columns)}")
        print(f"   Format: {output_config.get('format', 'parquet+zstd')}")
        print(f"   Output: {output_path}")
        print(f"   File Size: {file_size / 1024:.1f} KB")
        
        if record_count >= 100000:
            print(f"   Estimated compression ratio: {file_size / (record_count * len(unique_columns) * 10):.1f}x")

if __name__ == "__main__":
    main()