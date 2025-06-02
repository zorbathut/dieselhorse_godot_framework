import subprocess
import json
import requests
import sys
import os
from pathlib import Path
from collections import defaultdict
import time
import zipfile
import tempfile
import shutil
from urllib.parse import urljoin, urlparse
import re
import util
from bs4 import BeautifulSoup
import hashlib

util.cwdhack()

def load_whitelist_config(config_path):
    """Load the whitelist configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        whitelisted_packages = set(config.get('whitelisted_packages', []))
        whitelisted_license_hashes = set(config.get('whitelisted_license_hashes', []))
        
        print(f"Loaded whitelist config:")
        print(f"  - {len(whitelisted_packages)} whitelisted packages")
        print(f"  - {len(whitelisted_license_hashes)} whitelisted license hashes")
        
        return whitelisted_packages, whitelisted_license_hashes
        
    except FileNotFoundError:
        print(f"Warning: Whitelist config file '{config_path}' not found. All packages will be flagged as non-approved.")
        return set(), set()
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file '{config_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config file '{config_path}': {e}")
        sys.exit(1)

def hash_license_content(license_content):
    """Generate SHA-256 hash of license content for comparison."""
    if not license_content:
        return None
    
    # Normalize the content (remove extra whitespace, convert to lowercase)
    normalized = re.sub(r'\s+', ' ', license_content.strip().lower())
    
    # Generate SHA-256 hash
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def is_html_content(content):
    """Check if content appears to be HTML."""
    if not content:
        return False
    
    # Look for common HTML indicators
    html_indicators = [
        '<html', '<HTML', '<!DOCTYPE', '<!doctype',
        '<head>', '<HEAD>', '<body>', '<BODY>',
        '<div', '<DIV', '<p>', '<P>', '<span', '<SPAN'
    ]
    
    content_lower = content.lower().strip()
    return any(indicator.lower() in content_lower for indicator in html_indicators)

def is_spdx_content(soup):
    """Check if the HTML content is from SPDX."""
    # Look for SPDX-specific indicators
    spdx_indicators = [
        soup.find('h2', string='SPDX identifier'),
        soup.find('h2', string='SPDX web page'),
        soup.find(string=re.compile(r'licenses\.nuget\.org')),
        soup.find(string=re.compile(r'SPDX project')),
        soup.find('div', class_='optional-license-text'),
        soup.find('div', class_='replaceable-license-text')
    ]
    
    return any(indicator for indicator in spdx_indicators)

def extract_spdx_license_text(soup):
    """Extract just the license text from SPDX HTML, removing boilerplate."""
    try:
        # Start with the license title
        license_parts = []
        
        # Get the main license title (h1)
        title = soup.find('h1')
        if title:
            license_parts.append(title.get_text().strip())
        
        # Find the "License text" section and extract content after it
        license_text_header = soup.find('h2', string='License text')
        if license_text_header:
            # Get all siblings after the "License text" header until we hit "SPDX web page"
            current = license_text_header.next_sibling
            while current:
                # Stop if we hit the SPDX web page section or Notice section
                if (current.name == 'h2' and 
                    (current.get_text().strip() in ['SPDX web page', 'Notice'])):
                    break
                
                if current.name:  # It's a tag, not just text
                    # Include divs with license text classes and regular paragraphs
                    if (current.name in ['div', 'p'] and 
                        (not current.get('class') or 
                         any(cls in current.get('class', []) for cls in ['optional-license-text', 'replaceable-license-text']))):
                        license_parts.append(str(current))
                
                current = current.next_sibling
        else:
            # Fallback: if no "License text" header, look for the license content divs and paragraphs
            for element in soup.find_all(['div', 'p']):
                if (element.get('class') and 
                    any(cls in element.get('class') for cls in ['optional-license-text', 'replaceable-license-text'])):
                    license_parts.append(str(element))
                elif (element.name == 'p' and 
                      not element.find_parent(['h2']) and  # Not inside a header section
                      'SPDX' not in element.get_text() and
                      'licenses.nuget.org' not in element.get_text()):
                    license_parts.append(str(element))
        
        # Create new HTML with just the license content
        if license_parts:
            clean_html = '<html><body>' + ''.join(license_parts) + '</body></html>'
            return BeautifulSoup(clean_html, 'html.parser')
        
    except Exception as e:
        print(f"  Warning: Failed to extract SPDX license text: {e}")
    
    return soup  # Return original if extraction fails

def html_to_text(html_content):
    """Convert HTML content to plain text while preserving structure."""
    try:
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Handle SPDX content specially
        if is_spdx_content(soup):
            print(f"  Detected SPDX content, extracting license text only")
            soup = extract_spdx_license_text(soup)
        
        # Convert block elements to text with appropriate spacing
        # Handle paragraphs
        for p in soup.find_all('p'):
            p.insert_after('\n\n')
        
        # Handle line breaks
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # Handle other block elements (divs, headers, etc.)
        for tag in soup.find_all(['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'section', 'article']):
            tag.insert_after('\n\n')
        
        # Handle list items
        for li in soup.find_all('li'):
            li.insert_before('• ')
            li.insert_after('\n')
        
        # Handle lists (add extra spacing)
        for ul_ol in soup.find_all(['ul', 'ol']):
            ul_ol.insert_after('\n')
        
        # Get text content
        text = soup.get_text()
        
        # Clean up excessive whitespace while preserving paragraph structure
        # Replace multiple consecutive newlines with double newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up lines but preserve paragraph breaks
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line or (cleaned_lines and cleaned_lines[-1]):  # Keep empty lines that separate paragraphs
                cleaned_lines.append(cleaned_line)
        
        # Join lines and clean up final spacing
        text = '\n'.join(cleaned_lines)
        text = re.sub(r'\n\n\n+', '\n\n', text)  # Max 2 consecutive newlines
        text = text.strip()
        
        return text
    except Exception as e:
        print(f"  Warning: Failed to parse HTML content: {e}")
        # Fallback to simple tag removal with basic paragraph preservation
        text = re.sub(r'<p[^>]*>', '\n\n', html_content)
        text = re.sub(r'</p>', '', text)
        text = re.sub(r'<br[^>]*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()

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

def download_license_from_package(package_name, package_version, license_file_path):
    """Download license file from the actual NuGet package."""
    try:
        # Download the .nupkg file
        nupkg_url = f"https://api.nuget.org/v3-flatcontainer/{package_name.lower()}/{package_version}/{package_name.lower()}.{package_version}.nupkg"
        
        print(f"  Downloading package from: {nupkg_url}")
        response = requests.get(nupkg_url, timeout=30)
        
        if response.status_code == 200:
            # Create a temporary file to store the package
            with tempfile.NamedTemporaryFile(delete=False, suffix='.nupkg') as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            try:
                # Extract and find the license file
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    # Look for the license file (case insensitive)
                    license_content = None
                    for file_info in zip_ref.filelist:
                        if file_info.filename.lower() == license_file_path.lower():
                            with zip_ref.open(file_info.filename) as license_file:
                                license_content = license_file.read()
                                # Try to decode as UTF-8, fallback to latin-1
                                try:
                                    license_content = license_content.decode('utf-8')
                                except UnicodeDecodeError:
                                    license_content = license_content.decode('latin-1', errors='replace')
                                
                                # Check if content is HTML and convert if needed
                                if is_html_content(license_content):
                                    print(f"  Converting HTML license content to text")
                                    license_content = html_to_text(license_content)
                                
                                break
                    
                    return license_content
                    
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
    except Exception as e:
        print(f"  Error downloading package license: {e}")
    
    return None

def download_license_from_url(license_url):
    """Download license content from a URL."""
    try:
        print(f"  Downloading license from: {license_url}")
        
        # Handle common GitHub URLs that might need raw content
        if 'github.com' in license_url and '/blob/' in license_url:
            license_url = license_url.replace('/blob/', '/raw/')
        
        response = requests.get(license_url, timeout=30)
        if response.status_code == 200:
            content = response.text
            
            # Check if content is HTML and convert if needed
            if is_html_content(content):
                print(f"  Converting HTML license content to text")
                content = html_to_text(content)
            
            return content
        else:
            print(f"  Failed to download license: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"  Error downloading license from URL: {e}")
    
    return None

def get_license_info_and_content(package_name, package_version):
    """Get license information and actual license content."""
    
    # Get metadata from NuGet API
    url = f"https://api.nuget.org/v3-flatcontainer/{package_name.lower()}/{package_version}/{package_name.lower()}.nuspec"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, None
            
        # Parse the nuspec XML to extract license info
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        license_info = {}
        license_content = None
        
        # Extract metadata
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
        
        # Now try to get the actual license content
        if license_info.get('licenseType') == 'file' and license_info.get('license'):
            # License is a file in the package
            license_content = download_license_from_package(
                package_name, package_version, license_info['license']
            )
        elif license_info.get('licenseUrl'):
            # License is at a URL
            license_content = download_license_from_url(license_info['licenseUrl'])
        elif license_info.get('license') and license_info.get('license').startswith('http'):
            # Sometimes license field contains a URL
            license_content = download_license_from_url(license_info['license'])
        
        return license_info, license_content
        
    except Exception as e:
        print(f"  Error processing {package_name}: {e}")
        return None, None

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

def check_package_approval(package_name, license_content, whitelisted_packages, whitelisted_license_hashes):
    """Check if a package is approved based on package name or license hash."""
    
    # Check if package is whitelisted by name
    if package_name in whitelisted_packages:
        return True, "whitelisted_package", None
    
    # Check if license is whitelisted by hash
    if license_content:
        license_hash = hash_license_content(license_content)
        if license_hash in whitelisted_license_hashes:
            return True, "whitelisted_license", license_hash
        return False, "non_approved", license_hash
    
    # No license content available
    return False, "no_license", None

def collect_licenses(csproj_path, whitelisted_packages, whitelisted_license_hashes):
    """Main function to collect all licenses and check approvals."""
    print(f"Analyzing packages in {csproj_path}...")
    
    # Get package list from dotnet
    dotnet_output = run_dotnet_command(csproj_path)
    if not dotnet_output:
        return
    
    # Extract packages
    packages = extract_packages(dotnet_output)
    unique_packages = list(set(packages))  # Remove duplicates
    
    print(f"Found {len(unique_packages)} unique packages (including transitive dependencies)")
    
    # Collect license information and content
    license_data = {}
    license_contents = {}
    licenses_by_type = defaultdict(list)
    approval_results = {}
    non_approved_packages = []
    
    for i, (package_name, version) in enumerate(unique_packages, 1):
        print(f"Processing {i}/{len(unique_packages)}: {package_name} {version}")
        
        license_info, license_content = get_license_info_and_content(package_name, version)
        
        package_key = f"{package_name}@{version}"
        
        if license_info:
            license_data[package_key] = license_info
            
            if license_content:
                license_contents[package_key] = license_content
                print(f"  ✓ License content downloaded ({len(license_content)} chars)")
            else:
                print(f"  ⚠ License metadata found but content could not be downloaded")
            
            # Categorize by license type
            license_key = license_info.get('license') or license_info.get('licenseUrl', 'Unknown')
            licenses_by_type[license_key].append(package_key)
        else:
            license_data[package_key] = {"error": "Could not retrieve license information"}
            licenses_by_type['Unknown'].append(package_key)
            print(f"  ✗ Could not retrieve license information")
        
        # Check approval status
        is_approved, reason, license_hash = check_package_approval(
            package_name, license_content, whitelisted_packages, whitelisted_license_hashes
        )
        
        approval_results[package_key] = {
            'approved': is_approved,
            'reason': reason,
            'license_hash': license_hash
        }
        
        if not is_approved:
            non_approved_packages.append({
                'package': package_key,
                'reason': reason,
                'license_hash': license_hash
            })
            print(f"  ❌ NOT APPROVED: {reason}")
        else:
            print(f"  ✅ APPROVED: {reason}")
        
        # Rate limiting - be nice to the API
        time.sleep(0.2)
    
    return license_data, license_contents, licenses_by_type, approval_results, non_approved_packages

def generate_consolidated_license_file(license_data, license_contents, approval_results, output_file):
    """Generate a consolidated file with all license texts."""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CONSOLIDATED LICENSE FILE\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("This file contains the license texts for all third-party packages used in this project.\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write approval summary
        approved_count = sum(1 for result in approval_results.values() if result['approved'])
        total_count = len(approval_results)
        f.write(f"APPROVAL STATUS: {approved_count}/{total_count} packages approved\n\n")
        
        # Write table of contents
        f.write("TABLE OF CONTENTS\n")
        f.write("-" * 40 + "\n")
        for i, package_key in enumerate(sorted(license_contents.keys()), 1):
            approval_status = "✅" if approval_results.get(package_key, {}).get('approved') else "❌"
            f.write(f"{i:3d}. {approval_status} {package_key}\n")
        f.write("\n\n")
        
        # Write individual licenses
        for i, (package_key, license_content) in enumerate(sorted(license_contents.items()), 1):
            approval_info = approval_results.get(package_key, {})
            approval_status = "✅ APPROVED" if approval_info.get('approved') else "❌ NOT APPROVED"
            
            f.write("=" * 80 + "\n")
            f.write(f"{i}. {package_key} - {approval_status}\n")
            f.write("=" * 80 + "\n\n")
            
            # Add approval information
            f.write(f"Approval Status: {approval_status}\n")
            f.write(f"Approval Reason: {approval_info.get('reason', 'unknown')}\n")
            if approval_info.get('license_hash'):
                f.write(f"License Hash: {approval_info['license_hash']}\n")
            f.write("\n")
            
            # Add package metadata if available
            if package_key in license_data:
                info = license_data[package_key]
                if 'title' in info:
                    f.write(f"Package Title: {info['title']}\n")
                if 'authors' in info:
                    f.write(f"Authors: {info['authors']}\n")
                if 'copyright' in info:
                    f.write(f"Copyright: {info['copyright']}\n")
                if 'licenseUrl' in info:
                    f.write(f"License URL: {info['licenseUrl']}\n")
                f.write("\n")
            
            f.write("LICENSE TEXT:\n")
            f.write("-" * 40 + "\n")
            f.write(license_content)
            f.write("\n\n")
            
        # Add packages without license content
        packages_without_content = set(license_data.keys()) - set(license_contents.keys())
        if packages_without_content:
            f.write("=" * 80 + "\n")
            f.write("PACKAGES WITHOUT DOWNLOADABLE LICENSE CONTENT\n")
            f.write("=" * 80 + "\n\n")
            
            for package_key in sorted(packages_without_content):
                approval_info = approval_results.get(package_key, {})
                approval_status = "✅ APPROVED" if approval_info.get('approved') else "❌ NOT APPROVED"
                
                f.write(f"Package: {package_key} - {approval_status}\n")
                info = license_data.get(package_key, {})
                if 'licenseUrl' in info:
                    f.write(f"License URL: {info['licenseUrl']}\n")
                if 'license' in info:
                    f.write(f"License: {info['license']}\n")
                f.write("\n")

def generate_report(license_data, licenses_by_type, approval_results, non_approved_packages, output_file=None):
    """Generate a human-readable license summary report."""
    report = []
    report.append("=" * 80)
    report.append("LICENSE SUMMARY REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Approval summary
    approved_count = sum(1 for result in approval_results.values() if result['approved'])
    total_count = len(approval_results)
    report.append("APPROVAL SUMMARY")
    report.append("-" * 40)
    report.append(f"Total packages: {total_count}")
    report.append(f"Approved packages: {approved_count}")
    report.append(f"Non-approved packages: {total_count - approved_count}")
    report.append("")
    
    # Non-approved packages details
    if non_approved_packages:
        report.append("NON-APPROVED PACKAGES")
        report.append("-" * 40)
        for pkg_info in non_approved_packages:
            report.append(f"❌ {pkg_info['package']}")
            report.append(f"   Reason: {pkg_info['reason']}")
            if pkg_info['license_hash']:
                report.append(f"   License Hash: {pkg_info['license_hash']}")
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
            approval_info = approval_results.get(package, {})
            approval_status = "✅" if approval_info.get('approved') else "❌"
            report.append(f"  {approval_status} {package}")
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Summary report written to {output_file}")
    else:
        print(report_text)

def main():
    if len(sys.argv) < 2:
        print("Usage: python license_collector.py <path_to_csproj> [output_prefix] [config_file]")
        print("Example: python license_collector.py MyProject.csproj my_project whitelist_config.json")
        print("This will generate:")
        print("  - {output_prefix}_licenses.txt (consolidated license file)")
        print("  - {output_prefix}_summary.txt (summary report)")
        print("  - {output_prefix}_data.json (raw metadata)")
        print("If config_file is provided, packages will be checked against whitelist.")
        sys.exit(1)
    
    csproj_path = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "licenses"
    config_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    if not os.path.exists(csproj_path):
        print(f"Error: {csproj_path} does not exist")
        sys.exit(1)
    
    # Load whitelist configuration
    whitelisted_packages = set()
    whitelisted_license_hashes = set()
    
    if config_file:
        whitelisted_packages, whitelisted_license_hashes = load_whitelist_config(config_file)
    else:
        print("No config file provided. All packages will be flagged as non-approved.")
    
    try:
        license_data, license_contents, licenses_by_type, approval_results, non_approved_packages = collect_licenses(
            csproj_path, whitelisted_packages, whitelisted_license_hashes
        )
        
        # Generate consolidated license file
        license_file = f"{output_prefix}_licenses.txt"
        generate_consolidated_license_file(license_data, license_contents, approval_results, license_file)
        print(f"✓ Consolidated license file written to {license_file}")
        print(f"  Found license content for {len(license_contents)} out of {len(license_data)} packages")
        
        # Generate summary report
        summary_file = f"{output_prefix}_summary.txt"
        generate_report(license_data, licenses_by_type, approval_results, non_approved_packages, summary_file)
        
        # Save raw JSON data
        json_file = f"{output_prefix}_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': license_data,
                'license_contents': license_contents,
                'approval_results': approval_results
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Raw license data saved to {json_file}")
        
        # Report final approval status
        approved_count = sum(1 for result in approval_results.values() if result['approved'])
        total_count = len(approval_results)
        
        print(f"\n{'='*60}")
        print(f"FINAL APPROVAL STATUS: {approved_count}/{total_count} packages approved")
        
        if non_approved_packages:
            print(f"\n❌ NON-APPROVED PACKAGES ({len(non_approved_packages)}):")
            for pkg_info in non_approved_packages:
                print(f"  - {pkg_info['package']} ({pkg_info['reason']})")
                if pkg_info['license_hash']:
                    print(f"    License Hash: {pkg_info['license_hash']}")
            
            print(f"\n💡 To approve these packages, add them to your whitelist config:")
            print("   - Add package names to 'whitelisted_packages' array")
            print("   - Add license hashes to 'whitelisted_license_hashes' array")
            
            print(f"\n❌ APPROVAL CHECK FAILED: {len(non_approved_packages)} non-approved packages found")
            sys.exit(1)
        else:
            print(f"\n✅ APPROVAL CHECK PASSED: All packages are approved")
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()