#!/usr/bin/env python3
"""
Test script to debug VS Code JSON parsing issue.

This script helps diagnose and fix JSON5-like syntax issues in VS Code settings.json files.
"""

import json
import re
import os
import sys
from pathlib import Path

def sanitize_json5(content: str) -> str:
    """Sanitize JSON5-like content to valid JSON

    VS Code settings.json allows some JSON5 features like trailing commas,
    but Python's json module doesn't support them.

    Args:
        content: Raw JSON5-like content

    Returns:
        Sanitized JSON content
    """
    print("🔧 Sanitizing JSON5 syntax...")

    # Remove control characters that can break JSON parsing
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)

    # Remove trailing commas before closing brackets/braces
    # This handles cases like: { "key": "value", } or [ "item", ]
    original_content = content
    content = re.sub(r',(\s*[}\]])', r'\1', content)

    if content != original_content:
        print("  ✓ Removed trailing commas")

    # Remove single-line comments, but be careful not to remove // from URLs
    # Only remove // comments that start at beginning of line or after whitespace
    content = re.sub(r'(^|\s)//.*?$', r'\1', content, flags=re.MULTILINE)

    # Remove multi-line comments, but be more careful about context
    # Only remove /* */ that aren't part of strings (basic heuristic)
    lines = content.split('\n')
    cleaned_lines = []
    in_string = False
    escape_next = False

    for line in lines:
        cleaned_line = ""
        i = 0
        while i < len(line):
            char = line[i]

            if escape_next:
                cleaned_line += char
                escape_next = False
            elif char == '\\' and in_string:
                cleaned_line += char
                escape_next = True
            elif char == '"' and not escape_next:
                cleaned_line += char
                in_string = not in_string
            elif not in_string and i < len(line) - 1:
                if line[i:i+2] == '/*':
                    # Skip until */
                    j = line.find('*/', i + 2)
                    if j != -1:
                        i = j + 1  # Skip the */
                    else:
                        break  # Rest of line is comment
                else:
                    cleaned_line += char
            else:
                cleaned_line += char
            i += 1

        cleaned_lines.append(cleaned_line)

    return '\n'.join(cleaned_lines)

def test_json_parsing(file_path: str):
    """Test different approaches to parsing the JSON file"""

    print(f"🧪 Testing JSON parsing for: {file_path}")
    print("=" * 80)

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    # Read the file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✓ Successfully read file ({len(content)} characters)")
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

    # Test 1: Standard JSON parsing
    print("\n📋 Test 1: Standard JSON parsing")
    try:
        config = json.loads(content)
        print("✓ Standard JSON parsing successful!")
        print(f"  Keys: {list(config.keys())[:10]}...")  # Show first 10 keys
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Standard JSON parsing failed: {e}")
        print(f"   Error at line {e.lineno}, column {e.colno}")

        # Show the problematic area
        lines = content.split('\n')
        if e.lineno <= len(lines):
            start_line = max(0, e.lineno - 3)
            end_line = min(len(lines), e.lineno + 2)

            print("   Problematic area:")
            for i in range(start_line, end_line):
                marker = " >>> " if i == e.lineno - 1 else "     "
                print(f"   {marker}Line {i+1:3d}: {lines[i]}")

    # Test 2: JSON5 sanitization
    print("\n📋 Test 2: JSON5 sanitization approach")
    try:
        sanitized_content = sanitize_json5(content)
        config = json.loads(sanitized_content)
        print("✓ JSON5 sanitization successful!")
        print(f"  Keys: {list(config.keys())[:10]}...")  # Show first 10 keys

        # Check if MCP section exists
        if 'mcp' in config:
            print(f"  Found 'mcp' section with keys: {list(config['mcp'].keys())}")
        else:
            print("  No 'mcp' section found")

        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON5 sanitization also failed: {e}")
        print(f"   Error at line {e.lineno}, column {e.colno}")

        # Show differences between original and sanitized
        print("\n📝 Showing differences:")
        original_lines = content.split('\n')
        sanitized_lines = sanitized_content.split('\n')

        for i, (orig, san) in enumerate(zip(original_lines, sanitized_lines)):
            if orig != san:
                print(f"   Line {i+1:3d}:")
                print(f"     Original : {orig}")
                print(f"     Sanitized: {san}")

    # Test 3: Try to identify specific issues
    print("\n📋 Test 3: Identifying specific JSON issues")

    # Check for common JSON5 issues
    issues_found = []

    # Check for trailing commas
    if re.search(r',(\s*[}\]])', content):
        issues_found.append("Trailing commas found")

    # Check for comments
    if re.search(r'//.*?$', content, flags=re.MULTILINE):
        issues_found.append("Single-line comments (//) found")

    if re.search(r'/\*.*?\*/', content, flags=re.DOTALL):
        issues_found.append("Multi-line comments (/* */) found")

    # Check for unquoted keys
    if re.search(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:', content, flags=re.MULTILINE):
        issues_found.append("Potentially unquoted keys found")

    if issues_found:
        print("   Issues detected:")
        for issue in issues_found:
            print(f"     • {issue}")
    else:
        print("   No common JSON5 issues detected")

    return False

def main():
    """Main test function"""
    print("🧘 VS Code JSON Parsing Debug Tool")
    print("=" * 80)

    # Default VS Code settings path for macOS
    default_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")

    # Allow custom path via command line
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        test_path = default_path

    print(f"Target file: {test_path}")

    success = test_json_parsing(test_path)

    print("\n" + "=" * 80)
    if success:
        print("🎉 JSON parsing successful! The file can be read properly.")
        print("\n💡 Recommendations:")
        print("   • The VS Code settings.json file is valid")
        print("   • MCPM should be able to read this file")
        print("   • If you're still seeing errors, there may be a permissions issue")
    else:
        print("❌ JSON parsing failed. The file contains invalid JSON syntax.")
        print("\n💡 Recommendations:")
        print("   • Fix the JSON syntax errors shown above")
        print("   • Consider using the JSON5 sanitization approach in the client manager")
        print("   • Backup the file before making changes")
        print(f"   • You can fix manually or let MCPM create a backup and new file")

    print(f"\n🔍 File info:")
    try:
        stat = os.stat(test_path)
        print(f"   Size: {stat.st_size} bytes")
        print(f"   Permissions: {oct(stat.st_mode)[-3:]}")
        print(f"   Readable: {os.access(test_path, os.R_OK)}")
        print(f"   Writable: {os.access(test_path, os.W_OK)}")
    except Exception as e:
        print(f"   Could not get file info: {e}")

if __name__ == "__main__":
    main()
