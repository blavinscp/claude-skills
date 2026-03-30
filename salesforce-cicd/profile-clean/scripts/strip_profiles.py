#!/usr/bin/env python3
"""Strip out-of-scope metadata references from Salesforce profile and permission set files.

Parses package.xml to determine which metadata components are in the deployment,
then removes XML elements from .profile-meta.xml and .permissionset-meta.xml files
that reference metadata NOT in the package.

Exit codes:
    0 - Success
    1 - Runtime error (file not found, XML parse error, etc.)
    2 - Invalid arguments
"""

import argparse
import copy
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Salesforce metadata XML namespace
SF_NS = "http://soap.sforce.com/2006/04/metadata"
NS_MAP = {"sf": SF_NS}
NS_PREFIX = "{" + SF_NS + "}"

# Elements that should never be stripped (org-level settings, not metadata refs)
NEVER_STRIP_ELEMENTS = {"userPermissions", "loginIpRanges", "loginHours"}

# Mapping: profile/permset element tag -> (child key tag, package.xml type name)
ELEMENT_RULES = {
    "fieldPermissions": ("field", "CustomField"),
    "objectPermissions": ("object", "CustomObject"),
    "classAccesses": ("apexClass", "ApexClass"),
    "pageAccesses": ("apexPage", "ApexPage"),
    "tabVisibilities": ("tab", "CustomTab"),
    "recordTypeVisibilities": ("recordType", "RecordType"),
    "layoutAssignments": ("layout", "Layout"),
    "customPermissions": ("name", "CustomPermission"),
    "customMetadataTypeAccesses": ("name", "CustomMetadata"),
    "customSettingAccesses": ("name", "CustomObject"),
    "flowAccesses": ("flow", "Flow"),
    "applicationVisibilities": ("application", "CustomApplication"),
}

# Standard Salesforce objects (never strip references to these)
STANDARD_OBJECTS = {
    "Account", "Contact", "Opportunity", "Lead", "Case", "Campaign",
    "Contract", "Order", "Product2", "Pricebook2", "PricebookEntry",
    "Task", "Event", "User", "Solution", "Asset", "ContentDocument",
    "ContentVersion", "Document", "Attachment", "Note", "Report",
    "Dashboard", "EmailTemplate", "Folder", "Group", "Organization",
    "Profile", "PermissionSet", "UserRole", "OpportunityLineItem",
    "Quote", "QuoteLineItem", "CampaignMember", "ContactPointAddress",
    "Individual", "PersonAccount", "CaseComment", "FeedItem",
    "ContentDocumentLink", "ContentNote",
}


def parse_package_xml(manifest_path):
    """Parse package.xml and return a dict of {metadata_type: set(members)}.

    If a type has a wildcard member '*', all members of that type are considered
    in scope.
    """
    package = {}
    try:
        tree = ET.parse(manifest_path)
    except ET.ParseError as exc:
        print(f"Error: Failed to parse package.xml: {exc}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    root = tree.getroot()

    for types_elem in root.iter(f"{NS_PREFIX}types"):
        name_elem = types_elem.find(f"{NS_PREFIX}name")
        if name_elem is None or not name_elem.text:
            continue
        meta_type = name_elem.text.strip()
        members = set()
        for member_elem in types_elem.findall(f"{NS_PREFIX}members"):
            if member_elem.text:
                members.add(member_elem.text.strip())
        package[meta_type] = members

    return package


def is_managed_package_ref(value):
    """Check if a reference value belongs to a managed package (namespace prefix).

    Managed package references have the pattern: namespace__Name or
    namespace__Object__c.namespace__Field__c
    """
    if not value:
        return False
    # Split on '.' first to handle Object.Field patterns
    parts = value.split(".")
    for part in parts:
        segments = part.split("__")
        # A managed package ref has 3+ segments: namespace__Name__c
        # or is namespace__Name (2 segments where second is not 'c')
        # Simple custom objects: Name__c (2 segments, second is 'c')
        # Managed: ns__Name__c (3 segments) or ns__Name (2 segments, first is short namespace)
        if len(segments) >= 3:
            ns_candidate = segments[0]
            if 2 <= len(ns_candidate) <= 15 and ns_candidate.isalnum():
                return True
    return False


def is_standard_object(obj_name):
    """Check if an object name is a standard Salesforce object."""
    if not obj_name:
        return False
    return obj_name in STANDARD_OBJECTS or not obj_name.endswith("__c")


def is_standard_tab(tab_name):
    """Check if a tab is a standard object tab."""
    return tab_name.startswith("standard-") if tab_name else False


def should_strip_element(element_tag, ref_value, package_contents):
    """Determine whether a profile/permset element should be stripped.

    Returns (should_strip: bool, reason: str).
    """
    if element_tag in NEVER_STRIP_ELEMENTS:
        return False, "never-strip element"

    if element_tag not in ELEMENT_RULES:
        return False, "unknown element type"

    if not ref_value:
        return False, "no reference value"

    # Preserve managed package references
    if is_managed_package_ref(ref_value):
        return False, "managed package reference"

    _, pkg_type = ELEMENT_RULES[element_tag]

    # Wildcard: if package.xml has '*' for this type, keep everything
    if pkg_type in package_contents and "*" in package_contents[pkg_type]:
        return False, "wildcard member in package.xml"

    members = package_contents.get(pkg_type, set())

    # Element-specific logic
    if element_tag == "fieldPermissions":
        # ref_value is "Object.Field"
        obj_field = ref_value
        obj_name = ref_value.split(".")[0] if "." in ref_value else ref_value
        # Standard object field permissions are preserved
        if is_standard_object(obj_name):
            # Still check if the specific field is in CustomField members
            if obj_field in members or "*" in members:
                return False, "field in package"
            # For standard objects, preserve even if field not in package
            # (standard fields are safe to deploy)
            return False, "standard object field"
        # Custom object: check if object is in package
        obj_members = package_contents.get("CustomObject", set())
        if obj_name not in obj_members and "*" not in obj_members:
            return True, f"CustomObject '{obj_name}' not in package.xml"
        # Object is in package; check if field is in package
        if obj_field in members or "*" in members:
            return False, "field in package"
        return True, f"CustomField '{obj_field}' not in package.xml"

    elif element_tag == "objectPermissions":
        if is_standard_object(ref_value):
            return False, "standard object"
        if ref_value in members or "*" in members:
            return False, "object in package"
        return True, f"CustomObject '{ref_value}' not in package.xml"

    elif element_tag == "tabVisibilities":
        if is_standard_tab(ref_value):
            return False, "standard tab"
        if ref_value in members or "*" in members:
            return False, "tab in package"
        return True, f"CustomTab '{ref_value}' not in package.xml"

    elif element_tag == "recordTypeVisibilities":
        # ref_value is "Object.RecordTypeName"
        if ref_value in members or "*" in members:
            return False, "record type in package"
        obj_name = ref_value.split(".")[0] if "." in ref_value else ref_value
        rt_name = ref_value.split(".")[1] if "." in ref_value else ""
        if is_standard_object(obj_name) and rt_name == "Master":
            return False, "standard object Master record type"
        if is_managed_package_ref(obj_name):
            return False, "managed package object"
        return True, f"RecordType '{ref_value}' not in package.xml"

    elif element_tag == "layoutAssignments":
        # ref_value is "Object-Layout Name"
        if ref_value in members or "*" in members:
            return False, "layout in package"
        return True, f"Layout '{ref_value}' not in package.xml"

    else:
        # Generic check for classAccesses, pageAccesses, etc.
        if ref_value in members or "*" in members:
            return False, f"{pkg_type} in package"
        return True, f"{pkg_type} '{ref_value}' not in package.xml"


def find_profile_permset_files(source_dir, specific_files=None):
    """Find all .profile-meta.xml and .permissionset-meta.xml files."""
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    if specific_files:
        files = []
        for f in specific_files:
            full_path = source_path / f
            if full_path.is_file():
                files.append(full_path)
            else:
                print(f"Warning: File not found: {full_path}", file=sys.stderr)
        return files

    files = []
    for pattern in ("**/*.profile-meta.xml", "**/*.permissionset-meta.xml"):
        files.extend(source_path.glob(pattern))
    return sorted(files)


def is_admin_profile(file_path):
    """Check if a file is the Admin profile."""
    return Path(file_path).name == "Admin.profile-meta.xml"


def strip_file(file_path, package_contents, dry_run=False):
    """Process a single profile or permission set file.

    Returns a dict with file path and list of stripped elements.
    """
    result = {
        "file": str(file_path),
        "stripped": [],
        "skipped": False,
        "skip_reason": None,
    }

    if is_admin_profile(file_path):
        result["skipped"] = True
        result["skip_reason"] = "Admin profile"
        return result

    try:
        tree = ET.parse(file_path)
    except ET.ParseError as exc:
        result["skipped"] = True
        result["skip_reason"] = f"XML parse error: {exc}"
        return result

    root = tree.getroot()
    elements_to_remove = []
    managed_kept = 0

    for child in list(root):
        # Strip namespace prefix to get the local tag name
        tag = child.tag
        if tag.startswith(NS_PREFIX):
            tag = tag[len(NS_PREFIX):]

        if tag not in ELEMENT_RULES:
            continue

        key_tag, _ = ELEMENT_RULES[tag]
        key_elem = child.find(f"{NS_PREFIX}{key_tag}")
        if key_elem is None or not key_elem.text:
            continue

        ref_value = key_elem.text.strip()
        should_strip, reason = should_strip_element(tag, ref_value, package_contents)

        if should_strip:
            elements_to_remove.append((child, tag, ref_value, reason))
            result["stripped"].append({
                "element_type": tag,
                "reference": ref_value,
                "reason": reason,
            })
        elif "managed package" in reason:
            managed_kept += 1

    if elements_to_remove and not dry_run:
        for elem, _, _, _ in elements_to_remove:
            root.remove(elem)

        # Register namespace to avoid ns0: prefix in output
        ET.register_namespace("", SF_NS)

        # Write back with XML declaration
        tree.write(
            str(file_path),
            xml_declaration=True,
            encoding="UTF-8",
        )

        # ElementTree doesn't write a newline after the XML declaration on all
        # Python versions; normalise to ensure consistent output.
        raw = Path(file_path).read_bytes()
        if not raw.endswith(b"\n"):
            Path(file_path).write_bytes(raw + b"\n")

    result["managed_package_refs_kept"] = managed_kept
    return result


def format_text(report):
    """Format the report as human-readable text."""
    lines = []
    lines.append("Profile Clean Report")
    lines.append("=" * 50)
    mode = "DRY RUN (no files modified)" if report["summary"]["dry_run"] else "LIVE (files modified)"
    lines.append(f"Mode: {mode}")
    s = report["summary"]
    lines.append(
        f"Files scanned: {s['files_scanned']} | "
        f"Modified: {s['files_modified']} | "
        f"Elements stripped: {s['elements_stripped']}"
    )
    lines.append("")

    for detail in report["details"]:
        fname = detail["file"]
        if detail.get("skipped"):
            lines.append(f"{fname} (SKIPPED - {detail.get('skip_reason', 'unknown')})")
        elif detail["stripped"]:
            lines.append(f"{fname} ({len(detail['stripped'])} elements stripped)")
            for item in detail["stripped"]:
                lines.append(f"  - {item['element_type']}: {item['reference']} ({item['reason']})")
        else:
            lines.append(f"{fname} (no changes)")
        lines.append("")

    total_managed = sum(d.get("managed_package_refs_kept", 0) for d in report["details"])
    if total_managed:
        lines.append(f"Managed package references preserved: {total_managed}")

    return "\n".join(lines)


def format_json(report):
    """Format the report as JSON."""
    return json.dumps(report, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Strip out-of-scope metadata references from Salesforce profiles and permission sets.",
        epilog="Exit codes: 0=success, 1=runtime error, 2=invalid arguments",
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to package.xml manifest",
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Path to source directory containing profiles/permsets",
    )
    parser.add_argument(
        "--files",
        help="Comma-separated list of specific files to process (relative to source-dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    # Validate manifest path
    if not os.path.isfile(args.manifest):
        print(f"Error: Manifest file not found: {args.manifest}", file=sys.stderr)
        sys.exit(2)

    # Validate source directory
    if not os.path.isdir(args.source_dir):
        print(f"Error: Source directory not found: {args.source_dir}", file=sys.stderr)
        sys.exit(2)

    # Parse package.xml
    package_contents = parse_package_xml(args.manifest)

    # Find files to process
    specific_files = None
    if args.files:
        specific_files = [f.strip() for f in args.files.split(",") if f.strip()]

    files = find_profile_permset_files(args.source_dir, specific_files)

    if not files:
        report = {
            "summary": {
                "files_scanned": 0,
                "files_modified": 0,
                "elements_stripped": 0,
                "dry_run": args.dry_run,
            },
            "details": [],
            "preserved": {
                "admin_profile_skipped": False,
                "managed_package_refs_kept": 0,
            },
        }
    else:
        details = []
        for fpath in files:
            result = strip_file(fpath, package_contents, dry_run=args.dry_run)
            details.append(result)

        files_modified = sum(
            1 for d in details if d["stripped"] and not d.get("skipped")
        )
        elements_stripped = sum(len(d["stripped"]) for d in details)
        admin_skipped = any(d.get("skip_reason") == "Admin profile" for d in details)
        total_managed = sum(d.get("managed_package_refs_kept", 0) for d in details)

        report = {
            "summary": {
                "files_scanned": len(files),
                "files_modified": files_modified,
                "elements_stripped": elements_stripped,
                "dry_run": args.dry_run,
            },
            "details": details,
            "preserved": {
                "admin_profile_skipped": admin_skipped,
                "managed_package_refs_kept": total_managed,
            },
        }

    if args.format == "json":
        print(format_json(report))
    else:
        print(format_text(report))

    sys.exit(0)


if __name__ == "__main__":
    main()
