#!/usr/bin/env python3
"""
Validate functions before deployment.
Checks: syntax, required methods, metadata, etc.
"""

import ast
import sys
from pathlib import Path


class FunctionValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_file(self, file_path: Path) -> bool:
        """Validate a single function file"""

        print(f"\n🔍 Validating: {file_path.name}")

        with open(file_path, 'r') as f:
            content = f.read()

        # Check Python syntax
        try:
            ast.parse(content)
            print("   ✅ Syntax valid")
        except SyntaxError as e:
            self.errors.append(f"{file_path.name}: Syntax error - {str(e)}")
            print(f"   ❌ Syntax error: {str(e)}")
            return False

        # Check required metadata
        if 'title:' not in content:
            self.warnings.append(f"{file_path.name}: Missing 'title:' in docstring")

        if 'version:' not in content:
            self.warnings.append(f"{file_path.name}: Missing 'version:' in docstring")

        # Check for Tools class
        if 'class Tools:' not in content:
            self.errors.append(f"{file_path.name}: Missing 'class Tools'")
            print("   ❌ Missing required 'class Tools'")
            return False

        # Check for __user__ parameter handling
        if '__user__' not in content:
            self.warnings.append(f"{file_path.name}: No __user__ parameter (no RBAC)")

        print("   ✅ Structure valid")
        return True

    def validate_all(self) -> bool:
        """Validate all function files"""

        functions_dir = Path(__file__).parent.parent / 'functions'
        function_files = list(functions_dir.glob('client_*.py'))

        if not function_files:
            print("❌ No function files found")
            return False

        print(f"\n🔍 Validating {len(function_files)} functions...")

        results = []
        for func_file in function_files:
            results.append(self.validate_file(func_file))

        # Print summary
        print(f"\n{'='*50}")
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"   - {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")

        if all(results) and not self.errors:
            print("\n✅ All validations passed!")
            print(f"{'='*50}\n")
            return True
        else:
            print(f"\n❌ Validation failed")
            print(f"{'='*50}\n")
            return False


def main():
    validator = FunctionValidator()
    success = validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
