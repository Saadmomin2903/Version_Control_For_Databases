"""
Quality Check Utilities for Data Validation

Provides reusable quality check functions for the Silver layer
following the Write-Audit-Publish (WAP) pattern.
"""

from typing import List, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

class QualityCheckException(Exception):
    """Raised when a quality check fails"""
    pass

class QualityChecker:
    """Class for running data quality checks on DataFrames"""
    
    def __init__(self, df: DataFrame, table_name: str):
        self.df = df
        self.table_name = table_name
        self.checks_passed = []
        self.checks_failed = []
    
    def check_row_count(self, min_expected: int = 0, max_expected: int = None) -> 'QualityChecker':
        """
        Validate row count is within expected range
        
        Args:
            min_expected: Minimum acceptable row count
            max_expected: Maximum acceptable row count (None = no limit)
        """
        count = self.df.count()
        
        if count < min_expected:
            self.checks_failed.append({
                'check': 'row_count',
                'reason': f'Row count {count} below minimum {min_expected}'
            })
        elif max_expected and count > max_expected:
            self.checks_failed.append({
                'check': 'row_count',
                'reason': f'Row count {count} above maximum {max_expected}'
            })
        else:
            self.checks_passed.append({
                'check': 'row_count',
                'value': count,
                'range': f'{min_expected} to {max_expected or "unlimited"}'
            })
        
        return self
    
    def check_nulls(self, required_columns: List[str]) -> 'QualityChecker':
        """
       Check that required columns have no nulls
        
        Args:
            required_columns: List of column names that must not have nulls
        """
        for col_name in required_columns:
            null_count = self.df.filter(F.col(col_name).isNull()).count()
            
            if null_count > 0:
                self.checks_failed.append({
                    'check': 'null_check',
                    'column': col_name,
                    'reason': f'{null_count} null values found'
                })
            else:
                self.checks_passed.append({
                    'check': 'null_check',
                    'column': col_name,
                    'nulls': 0
                })
        
        return self
    
    def check_duplicates(self, key_columns: List[str]) -> 'QualityChecker':
        """
        Check for duplicate rows based on key columns
        
        Args:
            key_columns: Columns that should be unique
        """
        total_count = self.df.count()
        distinct_count = self.df.select(key_columns).distinct().count()
        duplicate_count = total_count - distinct_count
        
        if duplicate_count > 0:
            self.checks_failed.append({
                'check': 'duplicate_check',
                'keys': key_columns,
                'reason': f'{duplicate_count} duplicate rows found'
            })
        else:
            self.checks_passed.append({
                'check': 'duplicate_check',
                'keys': key_columns,
                'duplicates': 0
            })
        
        return self
    
    def check_value_range(self, column: str, min_val=None, max_val=None) -> 'QualityChecker':
        """
        Check that numeric column values are within acceptable range
        
        Args:
            column: Column name to check
            min_val: Minimum acceptable value
            max_val: Maximum acceptable value
        """
        if min_val is not None:
            below_min = self.df.filter(F.col(column) < min_val).count()
            if below_min > 0:
                self.checks_failed.append({
                    'check': 'value_range',
                    'column': column,
                    'reason': f'{below_min} values below {min_val}'
                })
        
        if max_val is not None:
            above_max = self.df.filter(F.col(column) > max_val).count()
            if above_max > 0:
                self.checks_failed.append({
                    'check': 'value_range',
                    'column': column,
                    'reason': f'{above_max} values above {max_val}'
                })
        
        if not any(c['check'] == 'value_range' and c.get('column') == column for c in self.checks_failed):
            self.checks_passed.append({
                'check': 'value_range',
                'column': column,
                'range': f'{min_val} to {max_val}'
            })
        
        return self
    
    def generate_report(self) -> str:
        """Generate quality check report"""
        report = []
        report.append("=" * 60)
        report.append(f"QUALITY CHECK REPORT: {self.table_name}")
        report.append("=" * 60)
        report.append("")
        
        # Passed checks
        if self.checks_passed:
            report.append(f"✓ PASSED CHECKS: {len(self.checks_passed)}")
            for check in self.checks_passed:
                check_type = check.pop('check')
                details = ', '.join(f"{k}={v}" for k, v in check.items())
                report.append(f"  ✓ {check_type}: {details}")
            report.append("")
        
        # Failed checks
        if self.checks_failed:
            report.append(f"✗ FAILED CHECKS: {len(self.checks_failed)}")
            for check in self.checks_failed:
                check_type = check.get('check')
                reason = check.get('reason')
                report.append(f"  ✗ {check_type}: {reason}")
            report.append("")
        
        # Summary
        total = len(self.checks_passed) + len(self.checks_failed)
        pass_rate = (len(self.checks_passed) / total * 100) if total > 0 else 0
        report.append(f"SUMMARY: {len(self.checks_passed)}/{total} checks passed ({pass_rate:.1f}%)")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def validate(self, raise_on_failure=True) -> bool:
        """
        Validate all checks and optionally raise exception
        
        Args:
            raise_on_failure: If True, raise QualityCheckException on failure
            
        Returns:
            True if all checks passed, False otherwise
        """
        report = self.generate_report()
        print(report)
        
        if self.checks_failed:
            if raise_on_failure:
                raise QualityCheckException(
                    f"{len(self.checks_failed)} quality checks failed for {self.table_name}"
                )
            return False
        
        return True

# Convenience function for quick checks
def run_quality_checks(df: DataFrame, table_name: str, 
                      min_rows: int = 0,
                      required_cols: List[str] = None,
                      unique_keys: List[str] = None) -> bool:
    """
    Run standard quality checks on a DataFrame
    
    Args:
        df: DataFrame to check
        table_name: Name for reporting
        min_rows: Minimum expected rows
        required_cols: Columns that must not have nulls
        unique_keys: Columns that should be unique
    
    Returns:
        True if all checks pass, False otherwise
    """
    checker = QualityChecker(df, table_name)
    checker.check_row_count(min_expected=min_rows)
    
    if required_cols:
        checker.check_nulls(required_cols)
    
    if unique_keys:
        checker.check_duplicates(unique_keys)
    
    return checker.validate(raise_on_failure=True)
