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

util.cwdhack()

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
    
    # Collect license information and content
    license_data = {}
    license_contents = {}
    licenses_by_type = defaultdict(list)
    
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
        
        # Rate limiting - be nice to the API
        time.sleep(0.2)
    
    return license_data, license_contents, licenses_by_type

def generate_consolidated_license_file(license_data, license_contents, output_file):
    """Generate a consolidated file with all license texts."""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("CONSOLIDATED LICENSE FILE\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("This file contains the license texts for all third-party packages used in this project.\n")
        f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Write table of contents
        f.write("TABLE OF CONTENTS\n")
        f.write("-" * 40 + "\n")
        for i, package_key in enumerate(sorted(license_contents.keys()), 1):
            f.write(f"{i:3d}. {package_key}\n")
        f.write("\n\n")
        
        # Write individual licenses
        for i, (package_key, license_content) in enumerate(sorted(license_contents.items()), 1):
            f.write("=" * 80 + "\n")
            f.write(f"{i}. {package_key}\n")
            f.write("=" * 80 + "\n\n")
            
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
                f.write(f"Package: {package_key}\n")
                info = license_data.get(package_key, {})
                if 'licenseUrl' in info:
                    f.write(f"License URL: {info['licenseUrl']}\n")
                if 'license' in info:
                    f.write(f"License: {info['license']}\n")
                f.write("\n")

def generate_report(license_data, licenses_by_type, output_file=None):
    """Generate a human-readable license summary report."""
    report = []
    report.append("=" * 80)
    report.append("LICENSE SUMMARY REPORT")
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
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"Summary report written to {output_file}")
    else:
        print(report_text)

def main():
    if len(sys.argv) < 2:
        print("Usage: python license_collector.py <path_to_csproj> [output_prefix]")
        print("Example: python license_collector.py MyProject.csproj my_project")
        print("This will generate:")
        print("  - {output_prefix}_licenses.txt (consolidated license file)")
        print("  - {output_prefix}_summary.txt (summary report)")
        print("  - {output_prefix}_data.json (raw metadata)")
        sys.exit(1)
    
    csproj_path = sys.argv[1]
    output_prefix = sys.argv[2] if len(sys.argv) > 2 else "licenses"
    
    if not os.path.exists(csproj_path):
        print(f"Error: {csproj_path} does not exist")
        sys.exit(1)
    
    try:
        license_data, license_contents, licenses_by_type = collect_licenses(csproj_path)
        
        # Generate consolidated license file
        license_file = f"{output_prefix}_licenses.txt"
        generate_consolidated_license_file(license_data, license_contents, license_file)
        print(f"✓ Consolidated license file written to {license_file}")
        print(f"  Found license content for {len(license_contents)} out of {len(license_data)} packages")
        
        # Generate summary report
        summary_file = f"{output_prefix}_summary.txt"
        generate_report(license_data, licenses_by_type, summary_file)
        
        # Save raw JSON data
        json_file = f"{output_prefix}_data.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': license_data,
                'license_contents': license_contents
            }, f, indent=2, ensure_ascii=False)
        print(f"✓ Raw license data saved to {json_file}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()