# Common Validation Failures

## Metadata Failures

### Missing Dependencies

**Error:** `In field: field_name - no CustomField named Account.Custom_Field__c found`

**Cause:** Deploying a component that references a field/object not in the target org or not in the package.

**Fix:**
1. Add the missing component to `package.xml`
2. Or deploy the dependency first in a separate package

### Duplicate Value

**Error:** `Duplicate value found: duplicates value on record with id: XXXXXXXXX`

**Cause:** Attempting to create a component that already exists with the same unique identifier.

**Fix:**
1. Check if the component already exists in the target org
2. Use `sf project retrieve` to compare source vs org state

### Profile/PermSet Reference Errors

**Error:** `Entity of type 'Profile' named 'Custom: Sales' cannot be found`

**Cause:** Profile references metadata not present in the target org.

**Fix:**
1. Run `/profile-clean` before validation
2. Strip field permissions for objects not in the deployment

## Test Failures

### System.DmlException

**Error:** `System.DmlException: Insert failed. REQUIRED_FIELD_MISSING`

**Cause:** Test data setup missing required fields, often after adding new required fields.

**Fix:**
1. Update test data factories to include the new required field
2. Check for validation rules that may block test data insertion

### System.QueryException

**Error:** `System.QueryException: List has no rows for assignment to SObject`

**Cause:** Test expects data that doesn't exist in the target org (hardcoded IDs or missing reference data).

**Fix:**
1. Use `@TestSetup` methods to create all test data
2. Never use hardcoded record IDs
3. Query for reference data dynamically

### Mixed DML Exception

**Error:** `MIXED_DML_OPERATION: DML operation on setup object is not permitted after you have updated a non-setup object`

**Cause:** Test performs DML on both setup (User, Group) and non-setup (Account, Contact) objects in the same transaction.

**Fix:**
1. Use `System.runAs()` to isolate setup object DML
2. Create users in `@TestSetup`, use them in test methods via `System.runAs()`

## Coverage Failures

### Overall Coverage Below 75%

**Error:** `Average test coverage across all Apex Classes and Triggers is XX%, at least 75% test coverage is required`

**Cause:** Org-wide test coverage has dropped below 75%.

**Fix:**
1. Run `parse_test_results.py` to identify classes with lowest coverage
2. Add tests for classes below 75%
3. Consider: is there dead code that should be deleted?

### Specific Class at 0%

**Cause:** New class deployed without any test coverage.

**Fix:**
1. Write test class covering the new code
2. Include the test class in the same deployment package

## OmniStudio Failures

### Unable to Resolve Reference

**Error:** `Unable to resolve reference to OmniProcess:ProcedureName`

**Cause:** OmniStudio components deployed out of order.

**Fix:**
1. Follow sequential deployment: DataRaptors -> IPs -> OmniScripts -> FlexCards
2. See [../references/omnistudio-sequencing.md](../../references/omnistudio-sequencing.md)

### FlexCard Activation Failure

**Error:** `Cannot activate FlexCard - dependent OmniScript not found`

**Cause:** FlexCard references an OmniScript that hasn't been deployed or activated yet.

**Fix:**
1. Deploy and activate OmniScripts before FlexCards
2. Verify all referenced OmniScripts are in the package

## Timeout Failures

### Validation Timeout

**Error:** `The deployment has been canceled due to a timeout`

**Cause:** Validation exceeded the maximum wait time (usually 60 minutes for large deployments).

**Fix:**
1. Split large deployments into smaller packages
2. Use `RunSpecifiedTests` instead of `RunLocalTests` to reduce test time
3. Investigate slow tests with `parse_test_results.py` duration analysis
