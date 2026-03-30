# Profile & Permission Set Stripping Rules

This reference defines which XML elements in `.profile-meta.xml` and `.permissionset-meta.xml` files should be stripped when their referenced metadata is not present in the deployment `package.xml`.

## Element-to-Package Mapping

Each profile/permset XML element references a specific metadata type. The table below maps element tag names to the package.xml `<types>` entry used to determine whether the reference is in scope.

| Profile/Permset Element | Child Key Element | Package.xml Type | Match Logic |
|------------------------|-------------------|------------------|-------------|
| `fieldPermissions` | `field` | `CustomField` | Value = `Object.Field`; both the object and field must be in package, OR the field must be listed under `CustomField` members |
| `objectPermissions` | `object` | `CustomObject` | Value = object API name; must appear under `CustomObject` members |
| `classAccesses` | `apexClass` | `ApexClass` | Value = class API name; must appear under `ApexClass` members |
| `pageAccesses` | `apexPage` | `ApexPage` | Value = page API name; must appear under `ApexPage` members |
| `tabVisibilities` | `tab` | `CustomTab` | Value = tab API name; must appear under `CustomTab` members. Note: standard tabs (e.g., `standard-Account`) are always preserved |
| `recordTypeVisibilities` | `recordType` | `RecordType` | Value = `Object.RecordTypeName`; must appear under `RecordType` members |
| `layoutAssignments` | `layout` | `Layout` | Value = `Object-LayoutName`; must appear under `Layout` members |
| `customPermissions` | `name` | `CustomPermission` | Value = permission API name; must appear under `CustomPermission` members |
| `customMetadataTypeAccesses` | `name` | `CustomMetadata` | Value = MDT API name; must appear under `CustomMetadata` members |
| `customSettingAccesses` | `name` | `CustomObject` | Custom settings are `CustomObject` types ending in `__c`; must appear under `CustomObject` members |
| `flowAccesses` | `flow` | `Flow` | Value = flow API name; must appear under `Flow` members |
| `userPermissions` | `name` | N/A | **Never strip** — user permissions are org-level settings, not metadata references |
| `applicationVisibilities` | `application` | `CustomApplication` | Value = app API name; must appear under `CustomApplication` members |
| `loginIpRanges` | N/A | N/A | **Never strip** — IP restrictions are security settings, not metadata references |
| `loginHours` | N/A | N/A | **Never strip** — login hour restrictions are security settings |

## Match Logic Details

### fieldPermissions

The `<field>` child contains a value like `Account.Custom_Field__c` or `CustomObj__c.Custom_Field__c`.

**Strip when:**
- The object portion is a custom object (`__c` suffix) AND is not listed under `CustomObject` members
- OR the full `Object.Field` value is not listed under `CustomField` members

**Preserve when:**
- The object is a standard object (Account, Contact, Opportunity, etc.) — standard object field permissions are generally safe to deploy
- The field is explicitly listed in `CustomField` members
- The field contains a namespace prefix (managed package)

### objectPermissions

The `<object>` child contains the object API name.

**Strip when:**
- The object is a custom object (`__c` suffix) not listed under `CustomObject` members

**Preserve when:**
- The object is a standard object
- The object contains a namespace prefix (managed package)

### tabVisibilities

The `<tab>` child contains the tab API name.

**Strip when:**
- The tab is a custom tab not listed under `CustomTab` members

**Preserve when:**
- The tab starts with `standard-` (standard object tab)
- The tab contains a namespace prefix

### recordTypeVisibilities

The `<recordType>` child contains `Object.RecordTypeName`.

**Strip when:**
- The record type is not listed under `RecordType` members

**Preserve when:**
- The value contains a namespace prefix
- The object is a standard object AND the record type is `Master` (default record type)

### layoutAssignments

The `<layout>` child contains `Object-Layout Name`.

**Strip when:**
- The layout is not listed under `Layout` members

**Preserve when:**
- The value contains a namespace prefix

## Edge Cases

### Admin Profile — Never Strip

The `Admin.profile-meta.xml` file must never be processed by the stripping tool. The Admin profile:
- Contains system administrator permissions that are foundational
- Is often deployed in full intentionally
- Removing elements can lock out administrators

**Implementation:** Skip any file whose basename is `Admin.profile-meta.xml`.

### Managed Package References — Always Preserve

Any element whose reference value contains a double-underscore namespace prefix (e.g., `npe01__`, `SBQQ__`) should be preserved regardless of package.xml contents. Managed package metadata is installed, not deployed, so it will never appear in your package.xml.

**Detection:** Check if the reference value matches the pattern `[a-zA-Z0-9]+__[a-zA-Z0-9]` where the prefix before `__` is 2-15 characters (namespace prefixes). Note: standard custom objects also end in `__c`, so the check is specifically for a namespace prefix pattern like `ns__ObjectName__c` or `ns__FieldName__c`.

**Simplified heuristic:** If the reference value contains `__` and the portion before the first `__` does not equal the portion that would make it a simple custom object (i.e., the value has three or more segments separated by `__`), treat it as managed.

### Wildcard Members in package.xml

If a `<types>` block contains `<members>*</members>`, ALL references of that type are in scope. Do not strip any elements of that type.

**Example:**
```xml
<types>
    <members>*</members>
    <name>CustomField</name>
</types>
```
This means all custom fields are in the deployment — preserve all `fieldPermissions` elements.

### Standard Value Sets

`fieldPermissions` for standard picklist fields (e.g., `Account.Industry`, `Lead.Status`) reference `StandardValueSet` metadata, not `CustomField`. These should always be preserved since standard value sets are rarely in package.xml.

### Profile vs Permission Set Differences

Both file types use the same XML elements, with one exception:
- **Profiles** include `layoutAssignments` and `loginIpRanges` — permission sets do not
- **Permission sets** may include `hasActivationRequired` — this is never stripped

The stripping rules apply identically to both file types for all shared elements.

## Before/After Examples

### Example 1: fieldPermissions Stripped

**package.xml contains:**
```xml
<types>
    <members>Account.Active__c</members>
    <name>CustomField</name>
</types>
```

**Before (profile XML):**
```xml
<fieldPermissions>
    <editable>true</editable>
    <field>Account.Active__c</field>
    <readable>true</readable>
</fieldPermissions>
<fieldPermissions>
    <editable>false</editable>
    <field>Account.Legacy_Id__c</field>
    <readable>true</readable>
</fieldPermissions>
```

**After (profile XML):**
```xml
<fieldPermissions>
    <editable>true</editable>
    <field>Account.Active__c</field>
    <readable>true</readable>
</fieldPermissions>
```

The `Legacy_Id__c` field permission was stripped because `Account.Legacy_Id__c` is not listed under `CustomField` members.

### Example 2: objectPermissions Stripped

**package.xml does NOT contain `CustomObj__c` under CustomObject.**

**Before:**
```xml
<objectPermissions>
    <allowCreate>true</allowCreate>
    <allowDelete>false</allowDelete>
    <allowEdit>true</allowEdit>
    <allowRead>true</allowRead>
    <modifyAllRecords>false</modifyAllRecords>
    <object>CustomObj__c</object>
    <viewAllRecords>false</viewAllRecords>
</objectPermissions>
```

**After:** Element is completely removed.

### Example 3: Managed Package Preserved

**package.xml does NOT contain any `SBQQ__` references.**

**Before:**
```xml
<fieldPermissions>
    <editable>true</editable>
    <field>SBQQ__Quote__c.SBQQ__Status__c</field>
    <readable>true</readable>
</fieldPermissions>
```

**After:** Element is preserved (managed package reference detected via `SBQQ__` namespace prefix).

### Example 4: classAccesses Stripped

**package.xml contains:**
```xml
<types>
    <members>AccountService</members>
    <name>ApexClass</name>
</types>
```

**Before:**
```xml
<classAccesses>
    <apexClass>AccountService</apexClass>
    <enabled>true</enabled>
</classAccesses>
<classAccesses>
    <apexClass>ContactBatch</apexClass>
    <enabled>true</enabled>
</classAccesses>
```

**After:**
```xml
<classAccesses>
    <apexClass>AccountService</apexClass>
    <enabled>true</enabled>
</classAccesses>
```

`ContactBatch` was stripped because it is not listed under `ApexClass` members in package.xml.
