
import subprocess
import json
import requests
import sys
import os
from pathlib import Path
from collections import defaultdict
import time
import util

util.cwdhack()

def run_dotnet_command(csproj_path):
    """Run dotnet list package command to get all packages."""
    try:
        # Get all packages including transitive dependencies
        result = subprocess.run([
            'dotnet', 'list', csproj_path, 'package', 
            '--include-transitive', '--format', 'json'
        ], capture_output=True, text=True, check=True)
        
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running dotnet command: {e}")
        print(f"Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON output: {e}")
        return None

def get_license_info(package_name, package_version):
    """Get license information from NuGet API."""
    
    # NuGet API v3 endpoint for package metadata
    url = f"https://api.nuget.org/v3-flatcontainer/{package_name.lower()}/{package_version}/{package_name.lower()}.nuspec"
    print(url)
    
    response = requests.get(url, timeout=10)
    if response.status_code == 200:

        # Parse the nuspec XML to extract license info
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        license_info = {}
        
        # Simple approach: iterate through ALL elements and find by tag name
        # This completely avoids namespace issues
        for elem in root.iter():
            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            
            if tag_name == 'license' and elem.text:
                license_info['license'] = elem.text.strip()
                if 'type' in elem.attrib:
                    license_info['licenseType'] = elem.attrib['type']
                    
            elif tag_name == 'licenseUrl' and elem.text:
                license_info['licenseUrl'] = elem.text.strip()
                
            elif tag_name == 'copyright' and elem.text:
                license_info['copyright'] = elem.text.strip()
                
            elif tag_name == 'title' and elem.text:
                license_info['title'] = elem.text.strip()
                
            elif tag_name == 'authors' and elem.text:
                license_info['authors'] = elem.text.strip()
            
        return license_info
        
    return None

def extract_packages(dotnet_output):
    """Extract package names and versions from dotnet output."""
    packages = []
    
    try:
        projects = dotnet_output.get('projects', [])
        for project in projects:
            frameworks = project.get('frameworks', [])
            for framework in frameworks:
                # Top-level dependencies
                top_level = framework.get('topLevelPackages', [])
                for pkg in top_level:
                    packages.append((pkg['id'], pkg['resolvedVersion']))
                
                # Transitive dependencies
                transitive = framework.get('transitivePackages', [])
                for pkg in transitive:
                    packages.append((pkg['id'], pkg['resolvedVersion']))
    except KeyError as e:
        print(f"Error parsing package structure: {e}")
        
    return packages

def collect_licenses(csproj_path):
    """Main function to collect all licenses."""
    print(f"Analyzing packages in {csproj_path}...")
    
    # Get package list from dotnet
    dotnet_output = run_dotnet_command(csproj_path)
    if not dotnet_output:
        return
    
    # Extract packages
    packages = extract_packages(dotnet_output)
    unique_packages = list(set(packages))  # Remove duplicates
    
    print(f"Found {len(unique_packages)} unique packages (including transitive dependencies)")
    
    # Collect license information
    license_data = {}
    licenses_by_type = defaultdict(list)
    
    for i, (package_name, version) in enumerate(unique_packages, 1):
        print(f"Processing {i}/{len(unique_packages)}: {package_name} {version}")
        
        license_info = get_license_info(package_name, version)
        if license_info:
            license_data[f"{package_name}@{version}"] = license_info
            
            # Categorize by license type
            license_key = license_info.get('license') or license_info.get('licenseUrl', 'Unknown')
            licenses_by_type[license_key].append(f"{package_name}@{version}")
        else:
            license_data[f"{package_name}@{version}"] = {"error": "Could not retrieve license information"}
            licenses_by_type['Unknown'].append(f"{package_name}@{version}")
        
        # Rate limiting - be nice to the API
        time.sleep(0.1)
    
    return license_data, licenses_by_type

def generate_report(license_data, licenses_by_type, output_file=None):
    """Generate a human-readable license report."""
    report = []
    report.append("=" * 80)
    report.append("LICENSE REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Summary by license type
    report.append("LICENSES SUMMARY")
    report.append("-" * 40)
    for license_type, packages in licenses_by_type.items():
        report.append(f"{license_type}: {len(packages)} packages")
    report.append("")
    
    # Detailed breakdown
    report.append("DETAILED BREAKDOWN")
    report.append("-" * 40)
    for license_type, packages in licenses_by_type.items():
        report.append(f"\n{license_type.upper()}:")
        for package in sorted(packages):
            report.append(f"  - {package}")
    
    report.append("")
    report.append("FULL PACKAGE DETAILS")
    report.append("-" * 40)
    for package, info in sorted(license_data.items()):
        report.append(f"\n{package}:")
        for key, value in info.items():
            report.append(f"  {key}: {value}")
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Report written to {output_file}")
    else:
        print(report_text)

def main():
    if len(sys.argv) < 2:
        print("Usage: python license_collector.py <path_to_csproj> [output_file]")
        print("Example: python license_collector.py MyProject.csproj licenses_report.txt")
        sys.exit(1)
    
    csproj_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(csproj_path):
        print(f"Error: {csproj_path} does not exist")
        sys.exit(1)
    
    try:
        license_data, licenses_by_type = collect_licenses(csproj_path)
        generate_report(license_data, licenses_by_type, output_file)
        
        # Also save raw JSON data
        json_file = "license_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(license_data, f, indent=2, ensure_ascii=False)
        print(f"Raw license data saved to {json_file}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
