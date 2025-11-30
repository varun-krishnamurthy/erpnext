# PostgreSQL Compatibility Implementation Guide

This guide provides step-by-step instructions for implementing PostgreSQL compatibility in ERPNext.

## Overview

ERPNext uses MariaDB-specific SQL functions in ~190 locations. This guide shows how to achieve full PostgreSQL compatibility with minimal code changes by:

1. Installing PostgreSQL proxy functions via `after_install` hook
2. Adding a DB-neutral fallback for the accounts receivable report

---

## Step 1: Add PostgreSQL Compatibility Functions

### File: `erpnext/setup/install.py`

Add the following function after the imports:

```python
def install_postgres_compatibility_functions():
    """
    Install MariaDB compatibility functions for PostgreSQL sites.
    These functions allow MariaDB SQL syntax to work on PostgreSQL.
    """
    if frappe.db.db_type == "postgres":
        frappe.db.sql("""
            -- IFNULL → COALESCE wrapper (fixes ~170 instances)
            CREATE OR REPLACE FUNCTION ifnull(a anyelement, b anyelement) 
            RETURNS anyelement AS $$ SELECT COALESCE(a, b); $$ LANGUAGE SQL IMMUTABLE;
            
            -- LOCATE → POSITION wrapper (fixes ~10 instances)
            CREATE OR REPLACE FUNCTION locate(needle text, haystack text) 
            RETURNS integer AS $$ SELECT POSITION(needle IN haystack); $$ LANGUAGE SQL IMMUTABLE;
            
            -- CURDATE wrapper
            CREATE OR REPLACE FUNCTION curdate() 
            RETURNS date AS $$ SELECT CURRENT_DATE; $$ LANGUAGE SQL IMMUTABLE;
            
            -- DATE_SUB wrapper
            CREATE OR REPLACE FUNCTION date_sub(d timestamp, i interval) 
            RETURNS timestamp AS $$ SELECT d - i; $$ LANGUAGE SQL IMMUTABLE;
            
            -- DATE_ADD wrapper  
            CREATE OR REPLACE FUNCTION date_add(d timestamp, i interval) 
            RETURNS timestamp AS $$ SELECT d + i; $$ LANGUAGE SQL IMMUTABLE;
        """)
        frappe.db.commit()
```

Then modify the existing `after_install()` function to call it:

```python
def after_install():
    # ... existing code ...
    install_postgres_compatibility_functions()
    frappe.db.commit()
```

---

## Step 2: Add DB-Neutral Fallback for Accounts Receivable

### File: `erpnext/accounts/report/accounts_receivable/accounts_receivable.py`

Find the `__init__` method (around line 60-70) and add the PostgreSQL fallback after the fetch method is determined:

```python
def __init__(self, filters=None):
    # ... existing code ...
    self.ple_fetch_method = (
        frappe.db.get_single_value("Accounts Settings", "receivable_payable_fetch_method")
        or "Buffered Cursor"
    )
    
    # Force DB-neutral method on PostgreSQL (Raw SQL uses MariaDB stored procedures)
    if frappe.db.db_type == "postgres" and self.ple_fetch_method == "Raw SQL":
        self.ple_fetch_method = "Buffered Cursor"
```

---

## Testing

### Prerequisites

1. A working Frappe/ERPNext development environment
2. PostgreSQL 13+ installed and configured

### Running Tests

#### Option 1: Run All Accounts Receivable Tests

```bash
# From frappe-bench directory
bench --site [your-postgres-site] run-tests --app erpnext --module erpnext.accounts.report.accounts_receivable.test_accounts_receivable
```

#### Option 2: Run Specific Test

```bash
bench --site [your-postgres-site] run-tests --app erpnext --test erpnext.accounts.report.accounts_receivable.test_accounts_receivable.TestAccountsReceivable
```

#### Option 3: Run Full Test Suite with PostgreSQL (CI Style)

To run tests like the CI pipeline:

```bash
# Add 'postgres' label to your PR to trigger PostgreSQL CI tests
# Or run locally:
cd ~/frappe-bench/
bench --site test_site run-parallel-tests --app erpnext --use-orchestrator
```

### Test Files to Verify

| Test File | What It Tests |
|-----------|---------------|
| `erpnext/accounts/report/accounts_receivable/test_accounts_receivable.py` | Accounts Receivable report functionality |
| `erpnext/accounts/doctype/sales_invoice/test_sales_invoice.py` | Sales invoice (uses `ifnull()` in queries) |
| `erpnext/accounts/doctype/payment_entry/test_payment_entry.py` | Payment entries |
| `erpnext/controllers/tests/test_queries.py` | Search queries (uses `LOCATE()`) |

### Manual Verification

After making changes, verify the following work on PostgreSQL:

1. **Search functionality**: Search for employees, leads, items, projects
2. **Accounts Receivable report**: Run with different fetch methods
3. **Date-based queries**: Fiscal year auto-creation, activation checks

---

## Verification Checklist

- [ ] `install_postgres_compatibility_functions()` added to `setup/install.py`
- [ ] Function called in `after_install()`
- [ ] PostgreSQL fallback added to `accounts_receivable.py`
- [ ] All tests pass on PostgreSQL site
- [ ] Search functionality works
- [ ] Accounts Receivable report generates correctly

---

## Troubleshooting

### Error: Function "ifnull" does not exist

The proxy functions haven't been installed. Run:

```bash
bench --site [your-postgres-site] execute erpnext.setup.install.install_postgres_compatibility_functions
```

### Error: "row type of" syntax error

You're using "Raw SQL" fetch method on PostgreSQL. Change to "Buffered Cursor" in:
**Accounts Settings → Receivable/Payable Fetch Method**

### Tests fail with database errors

Ensure your site is properly configured for PostgreSQL:

```bash
bench --site [your-site] show-config
```

Verify `db_type` is set to `postgres`.

---

## Files Changed Summary

| File | Change | Lines |
|------|--------|-------|
| `erpnext/setup/install.py` | Add `install_postgres_compatibility_functions()` | ~20 |
| `erpnext/accounts/report/accounts_receivable/accounts_receivable.py` | Add PostgreSQL fallback | ~3 |

**Total: ~23 lines of code for full PostgreSQL compatibility**
